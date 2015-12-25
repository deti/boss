import conf
import bottle
import logbook
import hmac
import base64
import hashlib
from decimal import Decimal
from model import db, autocommit, Customer, CustomerCard
from api import post, AdminApi
from api.check_params import check_params
from api.validator import String, Bool, JSON, Money, Integer
from utils.i18n import _


log_error = logbook.warning if conf.devel.system_test_warning else logbook.error


class PaymentsApi(AdminApi):
    ERROR_OK = 0
    ERROR_INVALID_INVOICE = 10
    ERROR_INVALID_AMOUNT = 11
    ERROR_COMMON = 13
    ERROR_OVERDUE = 20

    error_codes_info = {
        0: 'Платеж может быть проведен. Система выполнит авторизацию платежа',
        10: 'Неверный номер заказа. Платеж будет отклонен',
        11: 'Неверная сумма. Платеж будет отклонен',
        13: 'Платеж не может быть принят. Платеж будет отклонен',
        20: 'Платеж просрочен. Платеж будет отклонен, плательщик получит соответствующее уведомление',
    }

    mandatory_fields_pay = (
        # Billing mandatory fields:
        'AccountId',
        'Currency',
        # Cloudpayment mandatory fields:
        'TransactionId',
        'Amount',
        'Currency',
        'DateTime',
        'CardFirstSix',
        'CardLastFour',
        'CardType',
        'CardExpDate',
        'TestMode',
        'Status',)

    payment_info_fields = (
        'DateTime',
        'AccountId',
        'CardLastFour',
        'IpCity',
        'Amount',
        'Currency',
        'TransactionId',
        'TestMode',)

    @classmethod
    def get_request_hmac(cls, message, secret):
        secret = bytes(secret, encoding="utf-8")
        signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest()).decode()
        return signature

    @classmethod
    def check_request_auth(cls, info):
        # Check origin address
        remote_address = bottle.request.remote_addr
        if conf.payments.cloudpayments.origin_address != remote_address:
            if (len(bottle.request.remote_route) and
                    conf.payments.cloudpayments.origin_address != bottle.request.remote_route[0]):
                logbook.warning("[check_request_auth] Origin address is not valid - no origin in routes. "
                                "Remote: {}, remotes {}. Info: {}", remote_address, bottle.request.remote_route, info)
            else:
                logbook.warning("[check_request_auth] Origin address is not valid - remote addr is not origin. "
                                "Invalid remote addr {}. Info: {}", remote_address, info)

        # Check payment body HMAC
        headers_hmac = bottle.request.headers.get("Content-HMAC")
        request_data = bottle.request.body.read()
        request_data_hmac = cls.get_request_hmac(request_data, conf.payments.cloudpayments.api_secret)
        if request_data_hmac != headers_hmac:
            logbook.warning("[check_request_auth] Invalid body hmac. Data hmac:{}, header hmac:{}",
                            request_data_hmac,
                            headers_hmac)
            return False

        return True

    @classmethod
    def check_mandatory_fields(cls, request_data):
        for key in cls.mandatory_fields_pay:
            if key not in request_data:
                return False, key
        return True, ""

    @classmethod
    def validate_request(cls, request_data, info):
        mandatory_fields_check_res = cls.check_mandatory_fields(request_data)
        if not mandatory_fields_check_res[0]:
            return False, "Empty or absent mandatory field '%s' in info." % mandatory_fields_check_res[1]

        # Payment authorization
        if not cls.check_request_auth(info):
            return False, "Invalid auth."
        # check payment mode
        if request_data['TestMode'] != '0' and conf.payments.cloudpayments.allow_test_mode is not True:
            return False, "TestRequest in production mode."

        # Check payment status
        if request_data['Status'] != "Completed":
            # We should NOT accept payments with 'Authorized' status.
            # Please see here: https://cloudpayments.ru/Docs/Integration#schemes
            return False, "Invalid payment status %s" % request_data['Status']

        payment_amount = request_data['Amount']
        if not payment_amount or not float(payment_amount) > 0:
            return False, "Invalid payment amount: '%s'" % payment_amount

        return True, ""

    @post("payments/cloudpayments/check/")
    @check_params(
        AccountId=String, Amount=Money, AuthCode=String,
        CardExpDate=String, CardFirstSix=String, CardLastFour=String,
        CardType=String, Currency=String, Data=JSON,
        DateTime=String, Description=String, Email=String,
        InvoiceId=String, IpAddress=String, IpCity=String,
        IpCountry=String, IpDistrict=String, IpLatitude=String,
        IpLongitude=String, IpRegion=String, Name=String,
        PaymentAmount=String, PaymentCurrency=String, Status=String,
        TestMode=Bool, TransactionId=Integer)
    @autocommit
    def payment_check(self, *args, **request_data):
        """Checks payment availability for customer
            Parameters must be sent as json object.

        :param Int TransactionId: Mandatory - System transaction number.
        :param Numeric Amount: Mandatory - Payment amount from widget. Dot as separator, two digits after dot.
        :param String Currency: Mandatory - Currency: RUB/USD/EUR/GBP from widget parameters.
        :param String InvoiceId: Not mandatory - Order number from widget parameters.
        :param String AccountId: Mandatory - Customer identifier from widget parameters.
        :param String SubscriptionId: Not mandatory - Subscription identifier from widget parameters (for recurrent payments).
        :param String Name: Not mandatory - Card holder name.
        :param String Email: Payer's e-mail
        :param DateTime: Mandatory - Payment creation date/time in UTC (yyyy-MM-dd HH:mm:ss).
        :param String IpAddress: Not mandatory - Payer IP-address
        :param String IpCountry: Not mandatory - Payer's country double-chars code (according to ISO3166-1)
        :param String IpCity: Not mandatory - Payer's city
        :param String IpRegion: Not mandatory - Payer's region.
        :param String IpDistrict: Not mandatory - Payer's district.
        :param String CardFirstSix: Mandatory - Credit card first 6 digits
        :param String CardLastFour: Mandatory - Credit card last 6 digits
        :param String CardType: Mandatory - Card payment system: Visa or MasterCard or Maestro
        :param String CardExpDate: Mandatory - Card expiration date MM/YY
        :param String Issuer: Not mandatory - Issuer bank name
        :param String IssuerBankCountry: Not mandatory - Issuer bank country double-char code (according to ISO3166-1)
        :param String Description: Not mandatory - Payment description from widget parameters.
        :param Json Data: Not mandatory - Any json-data from widget.
        :param Bit TestMode: Mandatory - Test mode flag (1 or 0)
        :param String Status: Mandatory - Payment status: Completed — for single-step, Authorized — for double-step.

        :return: Status code, looks like {'code': 0}
        """
        logbook.info("[payment_check] Request info:{}", request_data)
        short_payment_info = dict([(key, request_data.get(key)) for key in PaymentsApi.payment_info_fields])

        # Common validation
        validation_res, validation_info = self.validate_request(request_data, short_payment_info)
        if not validation_res:
            log_error("[payment_check] {} Payment info: {}", validation_info, short_payment_info)
            return {'code': self.ERROR_COMMON}

        # Currency validation
        currency = request_data['Currency']
        if not currency or currency not in conf.currency.active:
            log_error("[payment_check] Invalid or incompatible currency: {}. Payment info: {}",
                      currency, short_payment_info)
            return {'code': self.ERROR_COMMON}

        # Customer validation
        customer_id = request_data['AccountId']
        customer = Customer.get_by_id(customer_id, False)
        if not customer:
            log_error("[payment_check] Customer {} not found. Payment info: {}", customer_id, short_payment_info)
            return {'code': self.ERROR_COMMON}
        if customer.is_test_mode():
            # Payments in test mode is not allowed
            logbook.warning("[payment_check] Customer {} in test mode. Payment info {}", customer, short_payment_info)
            return {'code': self.ERROR_COMMON}

        return {'code': self.ERROR_OK}

    @post("payments/cloudpayments/pay/")
    @check_params(
        AccountId=String, Amount=Money, AuthCode=String,
        CardExpDate=String, CardFirstSix=String, CardLastFour=String,
        CardType=String, Currency=String, Data=JSON,
        DateTime=String, Description=String, Email=String,
        InvoiceId=String, IpAddress=String, IpCity=String,
        IpCountry=String, IpDistrict=String, IpLatitude=String,
        IpLongitude=String, IpRegion=String, Name=String,
        PaymentAmount=String, PaymentCurrency=String, Status=String,
        TestMode=Bool, Token=String, TransactionId=Integer)
    @autocommit
    def payment_pay(self, *args, **request_data):
        """Checks payment availability for customer.
        Parameters must be sent as json object. Request data looks like:
        {
              'AccountId': '1000', # Customer ID here
              'Amount': '10.00',
              'AuthCode': 'A1B2C3',
              'CardExpDate': '10/15',
              'CardFirstSix': '424242',
              'CardLastFour': '4242',
              'CardType': 'Visa',
              'Currency': 'RUB',
              'Data': '{"myProp":"myProp value"}',
              'DateTime': '2015-08-05 06:54:46',
              'Description': 'Payment description',
              'Email': 'user@example.com',
              'InvoiceId': '1234567',
              'IpAddress': '46.251.83.16',
              'IpCity': 'Moscow',
              'IpCountry': 'RU',
              'IpDistrict': 'Moscow federal district',
              'IpLatitude': '56.329918',
              'IpLongitude': '44.009193',
              'IpRegion': 'Moscow district',
              'Name': 'CARDHOLDER NAME',
              'PaymentAmount': '10.00',  # Not found in documentation but exist in request
              'PaymentCurrency': 'RUB',  # No in docs
              'Status': 'Completed',
              'TestMode': '1',
              'Token': '477BBA133C182267FE5F086924ABDC5DB71F77BFC27F01F2843F2CDC69D89F05',
              'TransactionId': '1211506'
        }

        :param Int TransactionId: Mandatory - System transaction number.
        :param Numeric Amount: Mandatory - Payment amount from widget. Dot as separator, two digits after dot.
        :param String Currency: Mandatory - Currency: RUB/USD/EUR/GBP from widget parameters.
        :param String InvoiceId: Not mandatory - Order number from widget parameters.
        :param String AccountId: Mandatory - Customer identifier from widget parameters.
        :param String SubscriptionId: Not mandatory - Subscription identifier from widget parameters (for recurrent payments).
        :param String Name: Not mandatory - Card holder name.
        :param String Email: Payer's e-mail
        :param DateTime: Mandatory - Payment creation date/time in UTC (yyyy-MM-dd HH:mm:ss).
        :param String IpAddress: Not mandatory - Payer IP-address
        :param String IpCountry: Not mandatory - Payer's country double-chars code (according to ISO3166-1)
        :param String IpCity: Not mandatory - Payer's city
        :param String IpRegion: Not mandatory - Payer's region.
        :param String IpDistrict: Not mandatory - Payer's district.
        :param String CardFirstSix: Mandatory - Credit card first 6 digits
        :param String CardLastFour: Mandatory - Credit card last 6 digits
        :param String CardType: Mandatory - Card payment system: Visa or MasterCard or Maestro
        :param String CardExpDate: Mandatory - Card expiration date MM/YY
        :param String Issuer: Not mandatory - Issuer bank name
        :param String IssuerBankCountry: Not mandatory - Issuer bank country double-char code (according to ISO3166-1)
        :param String Description: Not mandatory - Payment description from widget parameters.
        :param Json Data: Not mandatory - Any json-data from widget.
        :param Bit TestMode: Mandatory - Test mode flag (1 or 0)
        :param String Status: Mandatory - Payment status: Completed — for single-step, Authorized — for double-step.
        :param String Token: Not mandatory - Card token for recurrent payments without card data.

        :return: Status code, looks like {'code': 0}
        """
        logbook.info("[payment_pay] Request info:{}", request_data)
        short_payment_info = dict([(key, request_data.get(key)) for key in PaymentsApi.payment_info_fields])

        # Common validation
        validation_res, validation_info = self.validate_request(request_data, short_payment_info)
        if not validation_res:
            log_error("[payment_pay] {} Payment info: {}", validation_info, short_payment_info)
            # Expected successful code (no other codes were accepted for pay)
            return {"code": self.ERROR_OK}

        # Currency validation
        currency = request_data['Currency']
        if not currency or currency not in conf.currency.active:
            log_error("[payment_pay] Invalid or incompatible currency: {}. Payment info: {}",
                      currency, short_payment_info)
            # Expected successful code (no other codes were accepted for pay)
            return {"code": self.ERROR_OK}

        # Customer validation
        customer_id = request_data['AccountId']
        customer = Customer.get_by_id(customer_id, False)
        if not customer:
            log_error("[payment_pay] Customer id '{}' not found. Payment info: {}",
                      customer_id, short_payment_info)
            # Expected successful code (no other codes were accepted for pay)
            return {"code": self.ERROR_OK}

        if customer.is_test_mode():
            # Payments in test mode is not allowed
            logbook.warning("[payment_pay] Customer {} in test mode. Payment info {}", customer, short_payment_info)
            return {'code': self.ERROR_OK}

        # Transaction validation
        transaction_id = request_data['TransactionId']
        transaction_count = customer.check_account_history_transaction(transaction_id)
        if transaction_count:
            # This transaction already processed
            logbook.warning("[payment_pay] Customer {}. Transaction already processed. Payment info {}",
                            customer, short_payment_info)
            return {'code': self.ERROR_OK}

        payment_description = _("Balance recharge via CloudPayments. Transaction: {}")

        # Process payment
        amount = Decimal(request_data['Amount'])
        customer.modify_balance(amount, currency, None,
                                payment_description.format(request_data['TransactionId']),
                                transaction_id=transaction_id)

        # Save customer's payment card for automated payments
        aux_data = request_data.get('Data')
        if aux_data and aux_data.get('saveAsDefault', False) is True:
            card_token = request_data.get("Token")
            if not card_token:
                log_error("[payment_pay] Customer {} wants to save card, but Token empty. Payment info: {}",
                          customer, short_payment_info)
            else:
                card = CustomerCard.add_card(customer_id, request_data['CardLastFour'], request_data['CardType'],
                                             card_token, active=True)
                logbook.info("[payment_pay] Customer {}. Add payment card: {}",
                             customer, card.display())

        # Expected successful code (no other codes were accepted for pay)
        return {"code": 0}
