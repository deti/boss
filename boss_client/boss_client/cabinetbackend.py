from . import BaseApiClient, Namespace, extract_parameters
import json


class CabinetBackendClient(BaseApiClient):
    API_VERSION = 0
    API_PREFIX = '/lk_api/' + str(API_VERSION)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = self._Customer(self)
        self.news = self._News(self)

    # noinspection PyUnusedLocal
    class _Customer(Namespace):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tariff = self._Tariff(self.client)
            self.subscription = self._Subscription(self.client)
            self.payments = self._Payments(self.client)
            self.auto_withdraw = self._AutoWithdraw(self.client)

        def create(self, email, password, detailed_info: dict=None, bot_secret=True, locale=None, promo_code=None):
            """
            POST customer/
            """
            data = extract_parameters()
            data.pop('bot_secret', None)
            return self.client.send_command_post('customer/', data=data, bot_secret=bot_secret,
                                                 json_data=True)['customer_info']

        def update(self, password=None, email=None, detailed_info: dict=None, locale=None):
            """
            PUT customer/me/
            """
            return self.client.send_command_put('customer/me/', data=extract_parameters(),
                                                json_data=True)['customer_info']

        def get(self):
            """
            GET customer/me/
            """
            return self.client.send_command_get('customer/me/')['customer_info']

        def confirm_email(self, token):
            """
            POST customer/confirm_email/<confirm_token>/
            :param str token: Token
            """
            return self.client.send_command_post('customer/confirm_email/{}/'.format(token))

        def send_confirm_email(self):
            """
            PUT customer/me/confirm_email/
            """
            return self.client.send_command_put('customer/me/confirm_email/')

        def invoice(self, amount, currency=None, date=None, number=None):
            """
            POST customer/me/invoice/
            """
            return self.client.send_command_post('customer/me/invoice/', data=extract_parameters())

        class _AutoWithdraw(Namespace):
            def get(self):
                """
                GET customer/me/payments/auto_withdraw/
                """
                return self.client.send_command_get('customer/me/payments/auto_withdraw/')

            def update(self, enabled=None, balance_limit=None, payment_amount=None):
                """
                POST customer/me/payments/auto_withdraw/
                """
                return self.client.send_command_post('customer/me/payments/auto_withdraw/', data=extract_parameters())

        class _Tariff(Namespace):
            def get(self):
                """
                GET customer/me/tariff/
                """
                return self.client.send_command_get('customer/me/tariff/')['tariff_info']

        class _Subscription(Namespace):
            path = 'customer/me/subscribe/'

            def get(self):
                """
                GET customer/me/subscribe/
                """
                return self.client.send_command_get(self)['subscribe']

            def update(self, subscribe):
                """
                PUT customer/me/subscribe/
                """
                return self.client.send_command_put(self, data=dict(subscribe=subscribe),
                                                    json_data=True)['subscribe']

        def question(self, subject, body, copy=None):
            """
            POST customer/support/
            """
            return self.client.send_command_post('customer/support/', data=extract_parameters())

        def balance_history(self, after=None, before=None, limit=None):
            """
            GET customer/me/balance/history/
            """
            return self.client.send_command_get('customer/me/balance/history/',
                                                data=extract_parameters())['account_history']

        def quota(self):
            """
            GET customer/me/quota/
            """
            return self.client.send_command_get('customer/me/quota/')['quota']

        def quota_used(self):
            """
            GET customer/me/used_quotas/
            """
            return self.client.send_command_get('customer/me/used_quotas/')

        def send_password_reset(self, email):
            """
            DELETE customer/password_reset/
            """
            return self.client.send_command_delete('customer/password_reset/', data=dict(email=email))

        def password_reset(self, token, password):
            """
            POST customer/password_reset/<password_token>/
            """
            return self.client.send_command_post('customer/password_reset/{}/'.format(token),
                                                 data=dict(password=password))

        def validate_password_reset(self, token):
            """
            GET customer/password_reset/<password_token>/
            :param str token:

            """
            return self.client.send_command_get('customer/password_reset/{}/'.format(token))

        def report(self, start, finish, report_format, report_type=None):
            """
            POST customer/me/report/
            """
            return self.client.send_command_post('customer/me/report/', data=extract_parameters())

        def os_login(self):
            """
            GET customer/me/os_login/
            """
            return self.client.send_command_get('customer/me/os_login/')

        def get_openstack_auth(self):
            """
            GET customer/me/os_token/
            """
            return self.client.send_command_get('customer/me/os_token/')

        def reset_os_password(self):
            """
            PUT customer/me/reset_os_password/
            """
            return self.client.send_command_put('customer/me/reset_os_password/')

        def make_prod(self):
            """
            POST customer/me/make_prod/
            """
            return self.client.send_command_post('customer/me/make_prod/')['customer_info']

        class _Payments(Namespace):
            def get_cards(self):
                """
                GET customer/payments/cloudpayments/card/
                """
                return self.client.send_command_get('customer/payments/cloudpayments/card/')['cards']

            def delete_card(self, card_id: int):
                """
                DELETE customer/payments/cloudpayments/card/
                """
                return self.client.send_command_delete('customer/payments/cloudpayments/card/',
                                                       data=dict(card_id=card_id))

    # noinspection PyUnusedLocal
    class _News(Namespace):
        def list(self, subject=None, body=None, visible=None, published=None, page=None, limit=None):
            """
            GET news/
            """
            return self.client.send_command_get('news/', data=extract_parameters())['news_list']

    def login(self, email, password, return_customer_info=False):
        """
        POST auth/
        """
        self.email = email
        self.password = password
        data = extract_parameters()
        data['return_customer_info'] = True
        customer_info = self.send_command_post('auth/', data=data)['customer_info']
        self.customer_id = customer_info['customer_id']
        if return_customer_info:
            return customer_info
        else:
            return {}

    def login_options(self):
        """
        OPTIONS auth/
        """
        return self.send_command_options('auth/')

    def logout(self):
        """
        POST logout/
        """
        return self.send_command_post('logout/')
