import conf
import json
import logbook
import requests
import posixpath
from arrow import utcnow
from decimal import Decimal
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth
from utils.i18n import preferred_language, _

from model import db, MessageTemplate
from task.mail import send_email
from api import request_base_url


class CloudpaymentsClient(object):

    @staticmethod
    def payment_proceed(amount, currency, customer_id, token,
                        customer_email=None, description=None):
        """
        :param amount:
        :param currency:
        :param customer_id:
        :param token:
        :param customer_email:
        :param description:
        :return:
            bool, dict - Transaction success status, additional info.
        """
        payload = {
            "Amount": amount,
            "Currency": currency,
            "AccountId": customer_id,
            "Token": token}
        if customer_email:
            payload.update({"Email": customer_email})
        if description:
            payload.update({"Description": description})

        logbook.info("[payment_preceed] Request payload: {}", payload)
        try:
            r = requests.post(conf.payments.cloudpayments.auto_payments_url,
                              json=payload,
                              auth=HTTPBasicAuth(conf.payments.cloudpayments.public_id,
                                                 conf.payments.cloudpayments.api_secret))
        except requests.exceptions.RequestException as e:
            logbook.error("[payment_proceed] Request exception: {}. Customer_id: {}", e, customer_id)
            return False, {}

        if r.status_code != 200:
            logbook.error("[payment_proceed] Invalid request for customer {}. Response:{}", customer_id, r.text)
            return False, {}

        response_data = r.json()
        if response_data['Success'] is not True:
            if response_data.get('Message'):
                logbook.error('[payment_proceed] Request fails for customer {}. Response: {}',
                              customer_id, response_data)
                return False, {}
            model_info = response_data.get('Model')
            if model_info:
                logbook.error('[payment_proceed] Payment rejected for customer {}. Response: {}',
                              customer_id, response_data)
                return False, model_info

        logbook.info("[payment_proceed] Request status code: {}; response: {}", r.status_code, r.text)
        return True, response_data


class PaymentService(object):

    @classmethod
    def withdraw(cls, card, amount, currency, customer, description):
        success, aux_info = CloudpaymentsClient.payment_proceed(amount, currency,
                                                                customer.customer_id, card.token,
                                                                customer.email, description)
        if not success:
            # Payment fails
            if aux_info:
                # Transaction rejected - disable this card
                card.change_status(card.STATUS_INVALID)
                # Send message to user
                cls.send_email_auto_payment_processed(customer, amount, currency, card.card_type, card.last_four,
                                                      aux_info['CardHolderMessage'], accepted=False)
            return
        # Cloudpayment should call back us for 'pay' method
        logbook.info('[withdraw] Customer:{} auto payment for {} {} successful.', customer, amount, currency)

    @classmethod
    def auto_withdraw(cls, customer, card):
        amount = Decimal(customer.auto_withdraw_amount)
        currency = customer.tariff.currency
        logbook.info('[auto_withdraw] Customer: {} amount: {}, currency: {}, card: {}', customer, amount, currency, card)

        request_description = _("Automated balance recharge via CloudPayments. Customer email: {}")
        PaymentService.withdraw(card, amount, currency, customer, request_description.format(customer.email))

    @classmethod
    def manual_withdraw(cls, customer, card, amount):
        assert isinstance(amount, Decimal)
        currency = customer.tariff.currency
        logbook.info('[manual_withdraw] Customer: {} amount: {}, currency: {}, card: {}', customer, amount, currency, card)

        request_description = _("Manual balance recharge via CloudPayments. Customer email: {}")
        PaymentService.withdraw(card, amount, currency, customer, request_description.format(customer.email))

    @staticmethod
    def send_email_about_balance_modifying(customer, delta, currency, balance, comment):
        assert isinstance(delta, Decimal)
        subscription_info = customer.subscription_info()['billing']
        if subscription_info['enable']:
            modifying_date = utcnow().datetime
            if delta > 0:
                template_id = MessageTemplate.CUSTOMER_RECHARGE
            else:
                template_id = MessageTemplate.CUSTOMER_WITHDRAW
            base_url = request_base_url()
            from api.cabinet.customer import CustomerApi
            url = urljoin(base_url, posixpath.join(CustomerApi.CABINET_FRONTEND_PATH, "transactions"))
            subject, body = MessageTemplate.get_rendered_message(template_id, language=customer.locale_language(),
                                                                 money={'money': abs(delta), 'currency': currency},
                                                                 balance={'money': balance, 'currency': currency},
                                                                 comment=comment,
                                                                 withdraw_date=modifying_date,
                                                                 transactions_url=url)
            send_email.delay(subscription_info['email'], subject, body)

    @classmethod
    def send_email_auto_payment_processed(cls, customer, delta, currency,
                                          card_type, card_last_four, comment, accepted=True):
        assert isinstance(delta, Decimal)
        subscription_info = customer.subscription_info()['billing']
        if subscription_info['enable']:
            modifying_date = utcnow().datetime
            if accepted:
                template_id = MessageTemplate.CUSTOMER_RECHARGE_AUTO
            else:
                template_id = MessageTemplate.CUSTOMER_RECHARGE_AUTO_REJECT

            base_url = request_base_url()
            from api.cabinet.customer import CustomerApi
            url = urljoin(base_url, posixpath.join(CustomerApi.CABINET_FRONTEND_PATH, "transactions"))

            subject, body = MessageTemplate.get_rendered_message(template_id,
                                                                 language=customer.locale_language(),
                                                                 money={'money': abs(delta), 'currency': currency},
                                                                 withdraw_date=modifying_date,
                                                                 card_type=card_type,
                                                                 card_last_four=card_last_four,
                                                                 transactions_url=url,
                                                                 comment=comment)
            send_email.delay(subscription_info['email'], subject, body)
