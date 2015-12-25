import mock
import errors
from tests.base import TestCaseApi
from model import db, Tariff
from decimal import Decimal
from api.admin.payments import PaymentsApi
from model.account.customer import CustomerCard, Customer
from service.payments import CloudpaymentsClient


class TestPaymentsApi(TestCaseApi):
    new_customer = {"email": "email@email.ru", "customer_type": "private",
                    "detailed_info": {"name": "test customer",
                                      "birthday": "1999-01-01",
                                      "country": "Russia",
                                      "city": "Moscow",
                                      "address": "Kreml, 1a",
                                      "telephone": "8(999)999 99 99"}}

    new_prod_customer = {"email": "email.prod@email.ru", "customer_type": "private",
                         "detailed_info": {"name": "test customer",
                                           "birthday": "1999-01-01",
                                           "country": "Russia",
                                           "city": "Moscow",
                                           "address": "Kreml, 1a",
                                           "telephone": "8(999)999 99 99",
                                           "passport_series_number": "1234 567 890",
                                           "passport_issued_by": "UFMS Russia",
                                           "passport_issued_date": "2013-01-01"}}
    transaction_id = 1

    def setUp(self):
        super().setUp()
        self.tariff = Tariff.create_tariff(self.localized_name("Tariff for customers"), "tariff!!!", "RUB", None)
        db.session.commit()

    @classmethod
    def get_request_data(cls, **kwargs):
        # Add payment
        cls.transaction_id += cls.transaction_id

        request_data = {
            'AccountId': '0',
            'Amount': '10.00',
            'AuthCode': 'A1B2C3',
            'CardExpDate': '10/15',
            'CardFirstSix': '424242',
            'CardLastFour': '4242',
            'CardType': 'Visa',
            'Currency': 'RUB',
            'Data': '{}',
            'DateTime': '2015-08-01 10:10:10',
            'Description': 'Payment for service usage, blah blah blah.',
            'Email': 'unknown@email.com',
            'InvoiceId': '1234567',
            'IpAddress': '127.0.0.1',
            'IpCity': 'Moscow',
            'IpCountry': 'RU',
            'IpDistrict': 'Moscow federal national circle of big circle',
            'IpLatitude': '56.329918',
            'IpLongitude': '44.009193',
            'IpRegion': 'Moscow',
            'Name': 'Unknown name',
            'PaymentAmount': '10.00',
            'PaymentCurrency': 'RUB',
            'Status': 'Completed',
            'TestMode': '1',
            'Token': '477BBA133C182267FE5F086924ABDC5DB71F77BFC27F01F2843F2CDC69D89F05',
            'TransactionId': cls.transaction_id
        }
        request_data.update(kwargs)
        return request_data

    def test_simple_payment(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        res = self.admin_client.payments.cloudpayments_pay(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]

        self.assertEqual(rub['balance'], '10.00')

    @mock.patch('api.admin.payments.log_error')
    def test_empty_request(self, lb):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add payment
        res = self.admin_client.payments.cloudpayments_pay({})
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]

        expected_call_args = ("[payment_pay] {} Payment info: {}",
                              "Empty or absent mandatory field 'AccountId' in info.",
                              dict.fromkeys(PaymentsApi.payment_info_fields),)

        self.assertEqual(1, lb.call_count)
        self.assertEqual(expected_call_args, lb.call_args[0])
        self.assertEqual(rub['balance'], '0.00')

    @mock.patch('api.admin.payments.conf.payments.cloudpayments')
    @mock.patch('api.admin.payments.log_error')
    def test_payment_in_production(self, lb, payments):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        payments.origin_address = '8.8.8.8'
        payments.allow_test_mode = False
        payments.api_secret = "1fa885be717b197d8815b633657c8dc5"

        request_data = self.get_request_data(**{
            'AccountId': str(cust_info['customer_id']),
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})

        res = self.admin_client.payments.cloudpayments_pay(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]

        self.assertEqual(1, lb.call_count)
        expected_call_args = ("[payment_pay] {} Payment info: {}",
                              "TestRequest in production mode.")
        self.assertEqual(expected_call_args, lb.call_args[0][:-1])
        self.assertEqual(rub['balance'], '0.00')

    @mock.patch('api.admin.payments.log_error')
    def test_unknown_customer(self, lb):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        request_data = self.get_request_data(**{
            'AccountId': 'Invalid value',
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})

        res = self.admin_client.payments.cloudpayments_pay(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]

        self.assertEqual(1, lb.call_count)
        expected_call_args = ("[payment_pay] Customer id '{}' not found. Payment info: {}",
                              request_data['AccountId'],)
        self.assertEqual(expected_call_args, lb.call_args[0][:-1])
        self.assertEqual(rub['balance'], '0.00')

    def test_check_simple(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})

        res = self.admin_client.payments.cloudpayments_check(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check balance is not changed
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '0.00')

    @mock.patch('api.admin.payments.log_error')
    def test_check_unknown_customer(self, lb):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        request_data = self.get_request_data(**{
            'AccountId': 'Invalid value',
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})

        res = self.admin_client.payments.cloudpayments_check(request_data)
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_COMMON})

        # Check balance is not changed
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '0.00')

        # Check error message
        self.assertEqual(1, lb.call_count)
        expected_call_args = ("[payment_check] Customer {} not found. Payment info: {}",
                              request_data['AccountId'],)
        self.assertEqual(expected_call_args, lb.call_args[0][:-1])

    def test_payment_cards(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Get user cards:
        cards = self.cabinet_client.customer.get_payment_cards()
        expected_user_cards = {
            "cards": [{
                "status": CustomerCard.status_info[CustomerCard.STATUS_ACTIVE],
                "last_four": "4242",
                "card_id": 1,
                "card_type": "Visa"
            }]
        }
        self.assertDictEqual(cards.json, expected_user_cards)

        # Delete card:
        cards = self.cabinet_client.customer.delete_payment_card(card_id=1)
        self.assertEqual(cards.json, {})

        # Get user cards:
        cards_after_delete = self.cabinet_client.customer.get_payment_cards()
        expected_user_cards_empty = {"cards": []}
        self.assertEqual(cards_after_delete.json, expected_user_cards_empty)

    def test_auto_payment(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add some money
        request_data = self.get_request_data(**{
            'Amount': '100.0',
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Change auto withdraw params
        change_result = self.cabinet_client.customer.auto_withdraw_change(False, 10, 500)

        # Check auto withdraw changed
        expected_auto_withdraw_params = {'enabled': False,
                                        'balance_limit': 10,
                                        'payment_amount': 500}
        res = self.cabinet_client.customer.auto_withdraw_get()
        self.assertEqual(expected_auto_withdraw_params, change_result.json)
        self.assertDictEqual(expected_auto_withdraw_params, res.json)

        # Check auto withdraw disabled
        with mock.patch("requests.post") as rp:
            # mock requests
            post_responce = mock.MagicMock()
            post_responce.status_code = 200
            post_responce.json = mock.MagicMock()
            post_responce.json.return_value = {}
            rp.return_value = post_responce

            from task.payments import task_check_customers_for_payment
            task_check_customers_for_payment()
            # Check - no calls for payments API
            self.assertEqual(post_responce.json.call_count, 0)
        # Check balance is not changed
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '110.00')

        # Change auto withdraw params - enable back
        self.cabinet_client.customer.auto_withdraw_change(True, 500, 3000)

        # Mock and run celery task
        with mock.patch("requests.post") as requests_post:
            # mock requests
            post_responce = mock.MagicMock()
            post_responce.status_code = 200
            post_responce.json = mock.MagicMock()
            post_responce.json.return_value = {
                "Model": {
                    "TransactionId": 504,
                    "Amount": 10.00000,
                    "Currency": "RUB",
                    "CurrencyCode": 0,
                    "InvoiceId": "1234567",
                    "AccountId": "user_x",
                    "Email": None,
                    "Description": "Payment for goods in example.com",
                    "JsonData": None,
                    "CreatedDate": "\/Date(1401718880000)\/",
                    "CreatedDateIso":"2014-08-09T11:49:41",  # all dates in UTC
                    "TestMode": True,
                    "IpAddress": "195.91.194.13",
                    "IpCountry": "RU",
                    "IpCity": "Moscow",
                    "IpRegion": "Moscow",
                    "IpDistrict": "Moscow federal district",
                    "IpLatitude": 54.7355,
                    "IpLongitude": 55.991982,
                    "CardFirstSix": "411111",
                    "CardLastFour": "1111",
                    "CardType": "Visa",
                    "CardTypeCode": 0,
                    "Issuer": "Sberbank of Russia",
                    "IssuerBankCountry": "RU",
                    "Status": "Declined",
                    "StatusCode": 5,
                    "Reason": "InsufficientFunds",  # reason of deny
                    "ReasonCode": 5051,
                    "CardHolderMessage": "Insufficient funds",  # message for customer
                    "Name": "CARDHOLDER NAME",
                },
                "Success": True,
                "Message": None
            }
            requests_post.return_value = post_responce

            from task.payments import task_check_customers_for_payment
            task_check_customers_for_payment()

            self.assertEqual(post_responce.json.call_count, 1)

        # Check balance not changed
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '110.00')

    def test_auto_payment_invalid_request(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add some money
        request_data = self.get_request_data(**{
            'Amount': '100.0',
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Enable auto withdraw for customer
        self.cabinet_client.customer.auto_withdraw_change(True, 1000, 2000)

        # Mock and run celery task
        with mock.patch("requests.post") as requests_post:
            # mock requests
            post_responce = mock.MagicMock()
            post_responce.status_code = 200
            post_responce.json = mock.MagicMock()
            post_responce.json.return_value = {"Success": False, "Message": "Amount is required"}
            requests_post.return_value = post_responce

            from task.payments import task_check_customers_for_payment
            task_check_customers_for_payment()

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '110.00')

    def test_auto_payment_invalid_credentials(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add some money
        request_data = self.get_request_data(**{
            'Amount': '100.0',
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Enable auto withdraw for customer
        self.cabinet_client.customer.auto_withdraw_change(True, 1000, 2000)

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Mock and run celery task
        with mock.patch("requests.post") as requests_post:
            # mock requests
            post_responce = mock.MagicMock()
            post_responce.status_code = 401
            post_responce.json = mock.MagicMock()
            post_responce.json.side_effect = ValueError('Should not call json while status_code is not 200.')
            requests_post.return_value = post_responce

            from task.payments import task_check_customers_for_payment
            task_check_customers_for_payment()

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '110.00')

    def test_auto_payment_transaction_rejected(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add some money
        request_data = self.get_request_data(**{
            'Amount': '100.0',
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Enable auto withdraw for customer
        self.cabinet_client.customer.auto_withdraw_change(True, 1000, 2000)

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Mock and run celery task
        with mock.patch("requests.post") as requests_post:
            # mock requests
            post_responce = mock.MagicMock()
            post_responce.status_code = 200
            post_responce.json = mock.MagicMock()
            post_responce.json.return_value = {
                "Model": {
                    "TransactionId": 504,
                    "Amount": 10.00000,
                    "Currency": "RUB",
                    "CurrencyCode": 0,
                    "InvoiceId": "1234567",
                    "AccountId": "user_x",
                    "Email": None,
                    "Description": "Payment for goods in example.com",
                    "JsonData": None,
                    "CreatedDate": "\/Date(1401718880000)\/",
                    "CreatedDateIso":"2014-08-09T11:49:41",  # all dates in UTC
                    "TestMode": True,
                    "IpAddress": "195.91.194.13",
                    "IpCountry": "RU",
                    "IpCity": "Moscow",
                    "IpRegion": "Moscow",
                    "IpDistrict": "Moscow federal district",
                    "IpLatitude": 54.7355,
                    "IpLongitude": 55.991982,
                    "CardFirstSix": "411111",
                    "CardLastFour": "1111",
                    "CardType": "Visa",
                    "CardTypeCode": 0,
                    "Issuer": "Sberbank of Russia",
                    "IssuerBankCountry": "RU",
                    "Status": "Declined",
                    "StatusCode": 5,
                    "Reason": "InsufficientFunds",  # reason of deny
                    "ReasonCode": 5051,
                    "CardHolderMessage": "Insufficient funds",  # message for customer
                    "Name": "CARDHOLDER NAME",
                },
                    "Success": False,
                    "Message": None
                }

            requests_post.return_value = post_responce

            from task.payments import task_check_customers_for_payment
            task_check_customers_for_payment()

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '110.00')

    def test_the_same_transaction(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()
        transaction_id = '100'

        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'TransactionId': transaction_id,
            'Amount': '10.00',
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        res = self.admin_client.payments.cloudpayments_pay(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check changed balance
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]

        self.assertEqual(rub['balance'], '10.00')

        # Send payment request with the same TransactionId again
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'TransactionId': transaction_id,
            'Amount': '10.00',
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        res = self.admin_client.payments.cloudpayments_pay(request_data)
        # Check mandatory response code for this request
        self.assertDictEqual(res.json, {'code': PaymentsApi.ERROR_OK})

        # Check balance is not changed
        cust_info = self.admin_client.customer.get(cust_info["customer_id"])
        rub = cust_info["account"]["RUB"]
        self.assertEqual(rub['balance'], '10.00')

    def test_manual_payment_stored_card(self):
        cust_info = self.cabinet_client.customer.create(password="superpassword",
                                                        make_prod=True, **self.new_prod_customer)
        customer = Customer.get_by_id(cust_info['customer_id'])
        customer.customer_mode = Customer.CUSTOMER_PRODUCTION_MODE
        db.session.commit()

        # Add some money
        request_data = self.get_request_data(**{
            'Amount': '100.0',
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name']})
        self.admin_client.payments.cloudpayments_pay(request_data)

        # Add card
        request_data = self.get_request_data(**{
            'AccountId': cust_info['customer_id'],
            'Data': '{"customer_id":"%s"}' % cust_info["customer_id"],
            'Email': cust_info['email'],
            'Name': cust_info['detailed_info']['name'],
            'Data': '{"saveAsDefault": true}'})
        self.admin_client.payments.cloudpayments_pay(request_data)

        cards = self.cabinet_client.customer.get_payment_cards().json

        with mock.patch.object(CloudpaymentsClient, 'payment_proceed', return_value=(True, {})) as pp:
            wihdraw_amount = 15
            res = self.cabinet_client.customer.withdraw_from_card(cards['cards'][0]['card_id'], wihdraw_amount).json
            self.assertIsNotNone(pp.call_args)
            self.assertEqual(cards['cards'][0], res)  # Check response
            self.assertEqual(pp.call_count, 1)
            self.assertEqual(pp.call_args[0][0], Decimal(wihdraw_amount))  # Check amount
            self.assertEqual(pp.call_args[0][1], 'RUB')  # Check withdraw currency
            self.assertEqual(pp.call_args[0][2], 1)  # Check customer_id
            self.assertEqual(pp.call_args[0][4], self.new_prod_customer['email'])  # Check email

            # Check invalid card number
            with self.expect_error(errors.PaymentCardNotFound):
                self.cabinet_client.customer.withdraw_from_card(100, wihdraw_amount)
            self.assertEqual(pp.call_count, 1)

            # Check invalid amount
            with self.expect_error(errors.BadRequest):
                self.cabinet_client.customer.withdraw_from_card(cards['cards'][0]['card_id'], -10)
            self.assertEqual(pp.call_count, 1)

            # Check deleted card
            self.cabinet_client.customer.delete_payment_card(cards['cards'][0]['card_id'])
            with self.expect_error(errors.PaymentCardNotFound):
                self.cabinet_client.customer.withdraw_from_card(cards['cards'][0]['card_id'], wihdraw_amount)
            self.assertEqual(pp.call_count, 1)
