from . import BaseApiClient, extract_parameters, Namespace
import json
import base64
import hashlib
import hmac


class AdminBackendClient(BaseApiClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = self._User(self)
        self.utility = self._Utility(self)
        self.service = self._Service(self)
        self.customer = self._Customer(self)
        self.tariff = self._Tariff(self)
        self.currency = self._Currency(self)
        self.news = self._News(self)
        self.reports = self._Reports(self)
        self.payments = self._Payments(self)
        self.stats = self._Stats(self)

    # noinspection PyUnusedLocal
    class _User(Namespace):
        def create(self, email, role, password=None, name=None):
            """
            POST user/ only manager
            """
            return self.client.send_command_post('user/', data=extract_parameters())['user_info']

        def update(self, user_id: int=None, password=None, name=None, email=None, role=None):
            """
            PUT user/me/
            PUT user/<user_id>/ only admin
            """
            data = extract_parameters()
            if user_id is None:
                data.pop('role', None)
                return self.client.send_command_put('user/me', data=data)['user_info']
            else:
                user_id = data.pop('user_id')
                return self.client.send_command_put('user/{}/'.format(user_id), data=data)['user_info']

        def get(self, user_id: int=None):
            """
            GET user/me/
            GET user/<user_id>/
            """
            if user_id is None:
                return self.client.send_command_get('user/me/')['user_info']
            else:
                return self.client.send_command_get('user/{}/'.format(user_id))['user_info']

        def delete(self, user_id: int=None):
            """
            DELETE user/me/
            DELETE user/<user_id>/ only admin
            """
            if user_id is None:
                return self.client.send_command_delete('user/me/')
            else:
                return self.client.send_command_delete('user/{}/'.format(user_id))

        def list(self, email=None, role=None, role_list=None, name=None, visibility=None, deleted_before=None,
                 deleted_after=None, last_login_before=None, last_login_after=None, created_before=None,
                 created_after=None, show_deleted=None, offset=0, limit=None, sort=None, all_parameters=True):
            """
            GET user/
            """
            return self.client.send_command_get('user/', data=extract_parameters())['user_list']

        def request_password_reset(self, email):
            """
            DELETE user/password_reset/
            """
            return self.client.send_command_delete('user/password_reset/', data={'email': email})

        def password_reset(self, password_token, password):
            """
            POST user/password_reset/<password_token>
            """
            return self.client.send_command_post('user/password_reset/{}/'.format(password_token),
                                                 data={'password': password})

        def validate_password_reset(self, password_token):
            """
            GET user/password_reset/is_valid/<password_token>/
            """
            return self.client.send_command_get('user/password_reset/{}/'.format(password_token))

    # noinspection PyUnusedLocal
    class _Utility(Namespace):
        def force_delete(self, tables, prefix, field=None):
            """
            DELETE _force_delete/ only admin
            """
            return self.client.send_command_delete('_force_delete/', data=extract_parameters())

        def role_list(self):
            """
            GET role/
            """
            return self.client.send_command_get('role/')['roles']

        def countries(self):
            """
            GET country/
            """
            return self.client.send_command_get('country/')['countries']

        def subscriptions(self):
            """
            GET subscription/
            """
            return self.client.send_command_get('subscription/')['subscriptions']

        def quota_templates(self):
            """
            GET quotas/templates/
            """
            return self.client.send_command_get('quotas/templates/')['quotas_templates']

        def languages(self):
            """
            GET language/
            """
            return self.client.send_command_get('language/')['language_list']

        def languages_active(self):
            """
            GET language/active/
            """
            return self.client.send_command_get('language/active/')['language_list']

        def locales_active(self):
            """
            GET locale/active/
            """
            return self.client.send_command_get('locale/active/')['locale_list']

        def send_email(self, send_to, subject=None, send_cc=None):
            """
            POST send_email/
            """
            return self.client.send_command_post('send_email/', data=extract_parameters())

    # noinspection PyUnusedLocal
    class _Service(Namespace):
        def list_categories(self):
            """
            GET category/
            """
            return self.client.send_command_get('category/')['category_list']

        def list_measure(self, measure_type=None):
            """
            GET measure/
            """
            return self.client.send_command_get('measure/', data=extract_parameters())['measure_list']

        def create(self, localized_name, measure, description=None):
            """
            POST service/custom/
            """
            return self.client.send_command_post('service/custom/', data=extract_parameters(),
                                                 json_data=True)['service_info']

        def create_vm(self, flavor_id, vcpus, ram, disk, network, localized_name, description=None):
            """
            POST service/vm/
            """
            return self.client.send_command_post('service/vm/', data=extract_parameters(),
                                                 json_data=True)['service_info']

        def get(self, service_id):
            """
            GET service/<service_id>/
            """
            return self.client.send_command_get('service/{}/'.format(service_id))['service_info']

        def delete(self, service_id: int):
            """
            DELETE service/<service_id>/ only admin
            """
            return self.client.send_command_delete('service/{}/'.format(service_id))

        def list(self, name=None, category=None, page=None, limit=None, sort=None):
            """
            GET service/
            """
            return self.client.send_command_get('service/', data=extract_parameters())['service_list']

        def update(self, service_id: int, localized_name=None, measure=None, description=None):
            """
            PUT service/<service>/custom/
            """
            return self.client.send_command_put('service/{}/custom/'.format(service_id), data=extract_parameters(True),
                                                json_data=True)['service_info']

        def update_vm(self, service_id: int, localized_name=None, description=None, flavor_id=None, vcpus=None,
                      ram=None, disk=None, network=None):
            """
            PUT service/<service>/vm/
            """
            return self.client.send_command_put('service/{}/vm/'.format(service_id), data=extract_parameters(True),
                                                json_data=True)['service_info']

        def immutable(self, service_id: int):
            """
            PUT service/<service>/immutable/
            """
            return self.client.send_command_put('service/{}/immutable/'.format(service_id))['service_info']

    # noinspection PyUnusedLocal
    class _Customer(Namespace):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tariff = self._Tariff(self.client)
            self.subscription = self._Subscription(self.client)
            self.deferred = self._Deferred(self.client)
            self.quota = self._Quota(self.client)
            self.auto_withdraw = self._AutoWithdraw(self.client)

        def make_prod(self, customer_id: int, comment=None):
            """
            POST customer/<customer_id>/make_prod/ only manager
            """
            return self.client.send_command_post('customer/{}/make_prod/'.format(customer_id),
                                                 data=extract_parameters(True))['customer_info']

        def create(self, email, password, detailed_info: dict=None, customer_type=None, locale=None,
                   bot_secret=True, make_prod=None, withdraw_period=None, promo_code=None):
            """
            POST customer/
            """
            data = extract_parameters()
            data.pop('bot_secret', None)
            return self.client.send_command_post('customer/', data=data, bot_secret=bot_secret,
                                                 json_data=True)['customer_info']

        def list(self, email=None, name=None, birthday=None, country=None, city=None, address=None, telephone=None,
                 blocked=None, customer_mode=None, customer_type=None, tariff_ids=None, created_before=None,
                 created_after=None, page=None, limit=None, sort=None, visibility=None):
            """
            GET customer/
            """
            return self.client.send_command_get('customer/', data=extract_parameters())['customer_list']

        def update(self, customer_id: int, password=None, detailed_info: dict=None,
                   tariff=None, comment=None, withdraw_period=None, locale=None, confirm_email=None):
            """
            PUT customer/<customer_id>/
            """
            return self.client.send_command_put('customer/{}/'.format(customer_id), data=extract_parameters(True),
                                                json_data=True)['customer_info']

        def get(self, customer_id: int):
            """
            GET customer/<customer_id>/
            """
            return self.client.send_command_get('customer/{}/'.format(customer_id))['customer_info']

        def delete(self, customer_id: int, comment=None):
            """
            DELETE customer/<customer_id>/ only manager
            """
            return self.client.send_command_delete('customer/{}/'.format(customer_id), data=dict(comment=comment))

        def options(self):
            """
            OPTIONS customer/
            """
            return self.client.send_command_options('customer/')

        def recreate_tenant(self, customer_id: int):
            """
            POST customer/<customer>/recreate_tenant/
            """
            return self.client.send_command_post('customer/{}/recreate_tenant/'.format(customer_id))

        def send_confirm_email(self, cutomer_id: int):
            """
            PUT customer/<customer_id>/confirm_email/
            """
            return self.client.send_command_put('customer/{}/confirm_email/'.format(cutomer_id))

        def invoice(self, customer_id: int, amount, currency=None, date=None, number=None):
            """
            POST customer/<customer_id>/invoice/
            """
            return self.client.send_command_post('customer/{}/invoice/'.format(customer_id),
                                                 data=extract_parameters(True))

        def group_update(self, customers, tariff=None, deferred_date=None, comment=None, withdraw_period=None,
                         balance_limit=None, customer_type=None, locale=None):
            """
            PUT customer/group/
            """
            return self.client.send_command_put('customer/group/', data=extract_parameters())['customer_info']

        class _AutoWithdraw(Namespace):
            def get(self, customer_id: int):
                """
                GET customer/<customer_id>/payments/auto_withdraw/
                """
                return self.client.send_command_get('customer/{}/payments/auto_withdraw/'.format(customer_id))

            def update(self, customer_id: int, enabled=None, balance_limit=None, payment_amount=None):
                """
                POST customer/<customer_id>/payments/auto_withdraw/
                """
                return self.client.send_command_post('customer/{}/payments/auto_withdraw/'.format(customer_id),
                                                     data=extract_parameters(True))

        class _Tariff(Namespace):
            def get(self, customer_id: int):
                """
                GET customer/<customer>/tariff/
                """
                return self.client.send_command_get('customer/{}/tariff/'.format(customer_id))['tariff_info']

        class _Subscription(Namespace):
            path = 'customer/{}/subscribe/'

            def get(self, customer_id: int):
                """
                GET customer/<customer>/subscribe/
                """
                return self.client.send_command_get(self(customer_id))['subscribe']

            def update(self, customer_id: int, subscribe):
                """
                PUT customer/<customer>/subscribe/
                """
                return self.client.send_command_put(self(customer_id), data=dict(subscribe=subscribe),
                                                    json_data=True)['subscribe']

        # noinspection PyUnusedLocal
        class _Deferred(Namespace):
            path = 'customer/{}/deferred/'

            def get(self, customer_id: int):
                """
                GET customer/<customer>/deferred/
                """
                return self.client.send_command_get(self(customer_id))['deferred']

            def update(self, customer_id: int, tariff, date, comment=None):
                """
                PUT customer/<customer>/deferred/
                """
                data = extract_parameters()
                data.pop('customer_id', None)
                return self.client.send_command_put(self(customer_id), data=data)['deferred']

            def delete(self, customer_id: int):
                """
                DELETE customer/<customer>/deferred/
                """
                return self.client.send_command_delete(self(customer_id))

            def force(self, customer_id: int):
                """
                POST customer/<customer>/deferred/force/
                """
                return self.client.send_command_post(self(customer_id) + 'force/')

        def update_balance(self, customer_id: int, amount, comment, currency=None):
            """
            PUT customer/<customer>/balance/
            """
            return self.client.send_command_put('customer/{}/balance/'.format(customer_id),
                                                data=extract_parameters(True))['customer_info']

        def block(self, customer_id: int, blocked: bool, message=None):
            """
            PUT customer/<customer>/block/
            """
            return self.client.send_command_put('customer/{}/block/'.format(customer_id),
                                                data=extract_parameters(True))['customer_info']

        def balance_history(self, customer_id: int, after=None, before=None, limit=None):
            """
            GEt customer/<customer>/balance/history/
            """
            return self.client.send_command_get('customer/{}/balance/history/'.format(customer_id),
                                                data=extract_parameters(True))['account_history']

        class _Quota(Namespace):
            path = 'customer/{}/quota/'

            def get(self, customer_id: int):
                """
                GET customer/<customer>/quota/
                """
                return self.client.send_command_get(self(customer_id))['quota']

            def update(self, customer_id: int, limits):
                """
                PUT customer/<customer>/quota/
                """
                return self.client.send_command_put(self(customer_id), data=dict(limits=limits))['quota']

            def update_template(self, customer_id: int, template):
                """
                POST customer/<customer>/quota/
                """
                return self.client.send_command_post(self(customer_id), data=dict(template=template))['quota']

        def history(self, customer_id: int, after=None, before=None, limit=None):
            """
            GET customer/<customer>/history/
            """
            return self.client.send_command_get('customer/{}/history/'.format(customer_id),
                                                data=extract_parameters(True))['history']

        def report(self, customer_id: int, start, finish, report_format, report_type=None):
            """
            POST customer/<customer>/report/
            """
            return self.client.send_command_post('customer/{}/report/'.format(customer_id),
                                                 data=extract_parameters(True))

        def fake_usage(self, customer_id: int, start, finish, service_id, resource_id, volume):
            """
            POST customer/<customer>/_fake_usage/
            """
            data = extract_parameters()
            data.pop('customer_id', None)
            return self.client.send_command_post('customer/{}/_fake_usage/'.format(customer_id),
                                                 data=data)

    # noinspection PyUnusedLocal
    class _Tariff(Namespace):
        def create(self, localized_name, description, currency, services=None, parent_id=None):
            """
            POST tariff/ only account
            """
            return self.client.send_command_post('tariff/', data=extract_parameters(), json_data=True)['tariff_info']

        def get(self, tariff_id: int):
            """
            GET tariff/<tariff_id>/
            """
            return self.client.send_command_get('tariff/{}/'.format(tariff_id))['tariff_info']

        def set_default(self, tariff_id: int):
            """
            PUT tariff/<tariff_id>/default/
            """
            return self.client.send_command_put('tariff/{}/default/'.format(tariff_id))['tariff_info']

        def get_default(self):
            """
            GET tariff/default/
            """
            return self.client.send_command_get('tariff/default/')['tariff_info']

        def update(self, tariff_id: int, localized_name=None, description=None, currency=None, services=None,
                   force_update=None):
            """
            PUT tariff/<tariff_id>/ only account
            """
            data = extract_parameters()
            data.pop('tariff_id', None)
            data = json.dumps(data)
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            return self.client.send_command_put('tariff/{}/'.format(tariff_id), data=data,
                                                headers=headers)['tariff_info']

        def list(self, name=None, description=None, currency=None, parent=None, visibility=None, page=None, limit=None,
                 sort=None):
            """
            GET tariff/
            """
            return self.client.send_command_get('tariff/', data=extract_parameters())['tariff_list']

        def delete(self, tariff_id: int):
            """
            DELETE tariff/<tariff_id>/ only account
            """
            return self.client.send_command_delete('tariff/{}/'.format(tariff_id))

        def immutable(self, tariff_id: int):
            """
            PUT tariff/<tariff_id>/immutable/ only account
            """
            return self.client.send_command_put('tariff/{}/immutable/'.format(tariff_id))['tariff_info']

        def get_history(self, tariff_id: int, history_id: int=None, date_before=None, date_after=None):
            """
            GET tariff/<tariff_id>/history/
            GET tariff/<tariff_id>/history/<history_id>/
            """
            data = extract_parameters()
            data.pop('tariff_id', None)
            if history_id is None:
                return self.client.send_command_get('tariff/{}/history/'.format(tariff_id), data=data)['tariff_history']
            else:
                data.pop('history_id', None)
                return self.client.send_command_get('tariff/{}/history/{}/'.format(tariff_id, history_id),
                                                    data=data)['tariff_history_info']

    # noinspection PyUnusedLocal
    class _Currency(Namespace):
        def create(self):
            """
            POST currency/
            """
            raise NotImplementedError

        def get(self):
            """
            GET currency/
            """
            return self.client.send_command_get('currency/')['currencies']

        def get_active(self):
            """
            GET currency/active/
            """
            return self.client.send_command_get('currency/active/')['currencies']

        def delete(self):
            """
            DELETE currency/
            """
            raise NotImplementedError

    # noinspection PyUnusedLocal
    class _News(Namespace):
        def create(self, subject, body):
            """
            POST news/ only manager
            """
            return self.client.send_command_post('news/', data=extract_parameters())['news_info']

        def list(self, subject=None, body=None, visible=None, published=None, page=None, limit=None):
            """
            GET news/
            """
            return self.client.send_command_get('news/', data=extract_parameters())['news_list']

        def update(self, news_id: int, subject=None, body=None):
            """
            PUT news/<news_id>/ only manager
            """
            return self.client.send_command_put('news/{}/'.format(news_id), data=extract_parameters(True))['news_info']

        def delete(self, news_id: int):
            """
            DELETE news/<news_id>/ only manager
            """
            return self.client.send_command_delete('news/{}/'.format(news_id))

        def publish(self, news_id: int, publish):
            """
            POST news/<news_id>/ only manager
            """
            return self.client.send_command_post('news/{}/'.format(news_id), data=dict(publish=publish))['news_info']

    # noinspection PyUnusedLocal
    class _Reports(Namespace):
        def receipts(self, start, finish, locale=None, report_format=None):
            """
            POST report/receipts/ only manager
            """
            return self.client.send_command_post('report/receipts/', data=extract_parameters())

        def usage(self, start, finish, locale=None, report_format=None):
            """
            POST report/usage/ only manager
            """
            return self.client.send_command_post('report/usage/', data=extract_parameters())

    # noinspection PyUnusedLocal
    class _Payments(Namespace):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cloudpayments = self._Cloudpayments(*args, **kwargs)

        class _Cloudpayments(Namespace):

            def _calc_hmac(self, json_dumped_data:str, api_secret):
                api_secret = bytes(api_secret, encoding='utf-8')
                data = bytes(json_dumped_data, encoding='utf-8')
                signature = base64.b64encode(hmac.new(api_secret, data, digestmod=hashlib.sha256).digest()).decode()
                return signature

            def check(self, api_secret, Status, TestMode, CardFirstSix, CardLastFour, DateTime, Email, Amount, Currency,
                      TransactionId, CardExpDate, CardType, AccountId=None, AuthCode=None, Data=None,
                      Description=None, InvoiceId=None, IpAddress=None, IpCity=None, IpCountry=None, IpDistrict=None,
                      IpLatitude=None, IpLongitude=None, IpRegion=None, Name=None, PaymentAmount=None, PaymentCurrency=None):
                """
                POST payments/cloudpayments/check/
                """
                data = extract_parameters()
                data.pop('api_secret')
                data = json.dumps(data)
                hmac = self._calc_hmac(data, api_secret)
                return self.client.send_command_post('payments/cloudpayments/check/', data=data,
                                                     headers={'Content-HMAC': hmac,
                                                              'Content-type': 'application/json',
                                                              'Accept': 'text/plain'})

            def pay(self, api_secret, Status, TestMode, CardFirstSix, CardLastFour, DateTime, Email, Amount, Currency,
                    TransactionId, CardExpDate, CardType, AccountId=None, AuthCode=None, Data=None, Token=None,
                    Description=None, InvoiceId=None, IpAddress=None, IpCity=None, IpCountry=None, IpDistrict=None,
                    IpLatitude=None, IpLongitude=None, IpRegion=None, Name=None, PaymentAmount=None, PaymentCurrency=None):
                """
                POST payments/cloudpayments/pay/
                """
                data = extract_parameters()
                data.pop('api_secret')
                data = json.dumps(data)
                hmac = self._calc_hmac(data, api_secret)
                return self.client.send_command_post('payments/cloudpayments/pay/', data=data,
                                                     headers={'Content-HMAC': hmac,
                                                              'Content-type': 'application/json',
                                                              'Accept': 'text/plain'})

    # noinspection PyUnusedLocal
    class _Stats(Namespace):
        def ips(self):
            """
            GET stat/ips/
            """
            return self.client.send_command_get('stat/ips/')['floating_ips']

        def customer(self):
            """
            POST stat/customer/
            """
            return self.client.send_command_post('stat/customer/')['customer_stats']

    def login(self, email, password, return_user_info: bool=False):
        """
        POST auth/
        """
        self.email = email
        self.password = password
        data = extract_parameters()
        data['return_user_info'] = True
        user_info = self.send_command_post('auth/', data=data)['user_info']
        self.user_id = user_info['user_id']
        self.name = user_info['name']
        if return_user_info:
            return user_info
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
