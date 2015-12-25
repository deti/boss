import conf
conf.test = True
import contextlib
import json
import os
import unittest
import posixpath
import logbook
import datetime
import time
from transliterate import translit
from model import db, database_config, User
from tests.bootstrap import BootstrapTest
from webtest import TestApp
from api import API_ADMIN, API_CABINET
from memdb import clear_mem_db
from utils import mail, setup_backend_logbook
from attrdict import AttrDict
from os_interfaces.openstack_wrapper import openstack
import keystoneclient.v2_0.client as ksclient
import mock
from model import Flavor
from novaclient.exceptions import NotFound


if db.config != database_config():
    raise Exception("Database models were created before import base. Config %s" % db.config)


def format_api_date(date):
    if isinstance(date, datetime.datetime):
        return date.strftime("%Y%m%d%H%M%S")
    elif isinstance(date, datetime.date):
        return date.strftime("%Y%m%d")
    assert "only datetime and date are accessible in this function"


def format_api_date_hour(date):
    if isinstance(date, datetime.datetime):
        return date.strftime("%Y%m%d%H")
    elif isinstance(date, datetime.date):
        return date.strftime("%Y%m%d00")
    assert "only datetime and date are accessible in this function"


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        logbook.info("------------- {} ---------", self)
        super().setUp()
        conf.customer.test_customer = {
            'test_period': {'blocking': 86400},
            "balance": {}
        }

    @classmethod
    def setUpClass(cls):
        handler = setup_backend_logbook("test")
        handler.push_application()

    def localized_name(self, name):
        return {"ru": translit(name, 'ru'), "en": name}


def Network(body):
    body['network']['id'] = 1
    return body


def Subnet(body):
    body['subnet']['id'] = 1
    return body


def Router(body):
    body['router']['id'] = 1
    return body


def truncate_tables():
    db.engine.execute("SET foreign_key_checks = 0;")
    tables = db.metadata.tables.values()
    query = ";".join(["TRUNCATE TABLE `%s`" % t.name for t in tables])
    db.engine.execute(query)
    db.engine.execute("SET foreign_key_checks = 1;")
    db.session.commit()


class BaseTestCaseDB(BaseTestCase):

    user_count = 0
    tenant_count = 0

    def bootstrap(self):
        b = BootstrapTest()
        fixture_dir = os.path.join(os.path.dirname(__file__), "fixture")
        b.process_doc(os.path.join(fixture_dir, "base.yaml"))

    @classmethod
    def create_user_mock(cls, name, password=None, email=None, tenant_id=None, enabled=True, **kwargs):
        cls.user_count += 1
        return AttrDict({"name": name, "username": name, "password": password, "tenantId": tenant_id,
                         "email": email, "enabled": enabled, "id": str(cls.user_count)})

    @classmethod
    def create_tenant_mock(cls, email, customer_id):
        cls.tenant_count += 1
        return AttrDict({'name': 'Test tenant', 'id': str(cls.tenant_count)})

    @classmethod
    def create_flavor_mock(cls, name):
        return AttrDict({'name': name, 'vcpus': 2, 'ram': 512, 'disk': 30})

    @classmethod
    def raise_flavor_notfound(cls, *args, **kwargs):
        raise NotFound('404')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        openstack.create_default_network = mock.MagicMock()
        openstack.create_default_subnet = mock.MagicMock()
        openstack.create_default_router = mock.MagicMock()
        #openstack.attach_subnet_to_router = mock.MagicMock()
        openstack.attach_flavors_to_tenant = mock.MagicMock()
        openstack.change_flavors = mock.MagicMock()
        openstack.create_flavor = mock.MagicMock()
        openstack.delete_flavor = mock.MagicMock()
        openstack.get_nova_flavor = mock.MagicMock(side_effect=cls.raise_flavor_notfound)
        openstack.change_tenant_quotas = mock.MagicMock()
        openstack.create_tenant = mock.MagicMock(side_effect=cls.create_tenant_mock)
        openstack.set_default_quotas = mock.MagicMock()
        openstack.set_default_user_role = mock.MagicMock()
        ksclient.Client = mock.MagicMock()
        openstack.client_keystone.users.create = mock.MagicMock(side_effect=cls.create_user_mock)
        openstack.client_keystone.users.list = mock.MagicMock(return_value=[])
        openstack.create_default_security_group_rule = mock.MagicMock()
        openstack.get_nova_servers = mock.MagicMock(return_value=[])
        openstack.get_volumes = mock.MagicMock(return_value=[])
        openstack.get_snapshots = mock.MagicMock(return_value=[])
        openstack.client_nova.images.list = mock.MagicMock(return_value=[])
        openstack.delete_vpns = mock.MagicMock()
        openstack.update_user_password = mock.MagicMock()
        vt = mock.Mock()
        vt.id = "ebb29578-fbf9-47e0-92ee-1766679b41e0"
        vt.name = "Standart"
        volume_types_list = [vt]
        openstack.client_cinder.volume_types.list = mock.MagicMock(return_value=volume_types_list)

    def setUp(self):
        mail.outbox[:] = []
        db.session.rollback()
        if getattr(conf, "created_db", False):
            truncate_tables()
        else:
            try:
                db.drop_all()
            except Exception as e:
                print(e)
            db.create_all()
            conf.created_db = True

        clear_mem_db()
        self.bootstrap()

        self.service_nano_id = Flavor.get_service_id('Nano')
        self.service_micro_id = Flavor.get_service_id('Micro')
        self.service_small_id = Flavor.get_service_id('Small')
        self.service_medium_id = Flavor.get_service_id('Medium')

        openstack._OpenStackAuth__auth["auth_url"] = "test.should.not.connect.to.open.stack.com"
        openstack.change_tenant_quotas = mock.MagicMock()
        openstack.update_user = mock.MagicMock()
        openstack.stop_instances = mock.MagicMock()
        openstack.start_instances = mock.MagicMock()
        openstack.client_neutron.create_network = mock.MagicMock(side_effect=Network)
        openstack.client_neutron.create_subnet = mock.MagicMock(side_effect=Subnet)
        openstack.client_neutron.create_router = mock.MagicMock(side_effect=Router)
        openstack.client_neutron.add_interface_router = mock.MagicMock()
        openstack.client_neutron.list_floatingips = mock.MagicMock(return_value={"floatingips": []})
        openstack.client_neutron.list_routers = mock.MagicMock(return_value={"routers": []})
        openstack.client_neutron.list_networks = mock.MagicMock(return_value={"networks": []})
        openstack.client_neutron.list_subnets = mock.MagicMock(return_value={"subnets": []})
        openstack.client_neutron.list_ports = mock.MagicMock(return_value={"ports": []})
        openstack.client_neutron.list_security_groups = mock.MagicMock(return_value={"security_groups": []})
        openstack.client_neutron.list_vpnservices = mock.MagicMock(return_value={"vpnservices": []})

        super().setUp()

    @property
    def admin_user(self):
        return User.get_by_email("boss@yourstack.com")


class ResponseError(Exception):
    def __init__(self, response):
        self.message = "<ResponseError(%d) >" % (response.status_int, )
        self.response = response


class BaseResourceApi:
    resource_name = ""
    prefix = "/api/0/"

    def __init__(self, client):
        self.client = client

    def url(self, resource_id=None):
        url = posixpath.join(self.prefix, self.resource_name) + "/"
        if resource_id:
            url += str(resource_id) + "/"
        return url

    @staticmethod
    def remove_none(params):
        return {name: value for name, value in params.items() if value is not None}


class BaseCRUD(BaseResourceApi):
    resource_info = ""
    resource_list = ""

    def create(self, as_json=False, **kwargs):
        res = self.client.post(self.url(), params=kwargs, as_json=as_json).json
        if self.resource_info:
            return res[self.resource_info]
        return res

    def list(self, **kwargs):
        res = self.client.get(self.url(), params=kwargs).json
        if self.resource_list:
            return res[self.resource_list]
        return res

    def get(self, resource_id):
        res = self.client.get(self.url(resource_id)).json
        if self.resource_info:
            return res[self.resource_info]
        return res

    def delete(self, resource_id):
        return self.client.delete(self.url(resource_id)).json

    def update(self, resource_id, as_json=False, **kwargs):
        res = self.client.put(self.url(resource_id), params=kwargs, as_json=as_json).json
        if self.resource_info:
            return res[self.resource_info]
        return res


class UserCRUD(BaseCRUD):
    resource_name = "user"

    def reset_password_valid(self, token):
        return self.client.get(self.url("password_reset/" + token), auth_required=False).json

    def reset_password(self, token, new_password):
        return self.client.post(self.url("password_reset/" + token),
                                params={"password": new_password},
                                auth_required=False).json

    def request_reset_password(self, email):
        return self.client.delete(self.url("password_reset"),
                                  params={"email": email},
                                  auth_required=False).json


class ServiceCRUD(BaseCRUD):
    resource_name = "service"
    resource_info = "service_info"

    def categories(self):
        return self.client.get(posixpath.join(self.prefix, "category")).json["category_list"]

    def create_custom(self, localized_name, measure, description=None):
        params = {"localized_name": localized_name,
                  "measure": measure,
                  "description": description}
        res = self.client.post(self.url("custom"), params=params, as_json=True).json
        if self.resource_info:
            return res[self.resource_info]
        return res

    def create_vm(self, **params):
        res = self.client.post(self.url("vm"), params=params, as_json=True).json[self.resource_info]
        return res

    def immutable(self, tariff_id):
        return self.client.put(self.url("%s/immutable" % tariff_id)).json["service_info"]

    def update_vm(self, resource_id, as_json=False, **kwargs):
        return self.update("%s/vm" % resource_id, as_json, **kwargs)

    def update_custom(self, resource_id, as_json=False, **kwargs):
        return self.update("%s/custom" % resource_id, as_json, **kwargs)

    def measures(self, measure_type=None):
        params = {}
        if measure_type:
            params["measure_type"] = measure_type
        return self.client.get(posixpath.join(self.prefix, "measure"),
                               params=params).json["measure_list"]


class Currency(BaseResourceApi):
    resource_name = "currency"

    def list(self):
        return self.client.get(self.url()).json["currencies"]

    def list_active(self):
        return self.client.get(self.url("active")).json["currencies"]


class Deferred(BaseCRUD):
    prefix = None
    resource_name = "deferred"
    resource_info = "deferred"

    def __init__(self, client, customer_id):
        super().__init__(client)
        self.prefix = posixpath.join("/api/0/customer/", str(customer_id))

    def get(self, resource_id=""):
        return super().get("")

    def delete(self, resource_id=""):
        return super().delete(resource_id)

    # noinspection PyMethodOverriding
    def update(self, tariff, date, resource_id="", as_json=False, ):
        return super().update(resource_id, as_json=as_json, tariff=tariff, date=format_api_date(date))

    def force(self):
        return self.client.post(self.url("force"))


class QuotaCRUD(BaseCRUD):
    prefix = None
    resource_name = "quota"
    resource_info = "quota"

    def __init__(self, client, customer_id):
        super().__init__(client)
        self.prefix = posixpath.join(client.customer.prefix, "customer/", customer_id)

    def get(self, resource_id=""):
        return super().get("")

    def update(self, resource_id="", as_json=True, **kwargs):
        return super().update(resource_id, as_json=as_json, **kwargs)

    def change_template(self, params):
        return self.client.post(self.url(), params=params).json[self.resource_info]


class CustomerCRUD(BaseCRUD):
    prefix = "/lk_api/0/"
    resource_name = "customer"
    resource_info = "customer_info"
    resource_list = "customer_list"

    def create(self, bot_secret=True, **kwargs):
        params = kwargs.copy()
        if bot_secret:
            params["bot_secret"] = True
        return self.client.post(self.url(), params=params, auth_required=False, as_json=True).json["customer_info"]

    def update(self, resource_id, **kwargs):
        return super(CustomerCRUD, self).update(resource_id, as_json=True, **kwargs)

    def confirm_email(self, confirm_token):
        return self.client.post(self.url("confirm_email/%s" % confirm_token),
                                auth_required=False).json["password_token"]

    def request_confirm_email(self, customer_id="me"):
        self.client.put(self.url("%s/confirm_email" % customer_id))

    def os_login(self):
        return self.client.get(self.url("me/os_login"))

    def os_token(self):
        return self.client.get(self.url("me/os_token"))

    def get_tariff(self, customer_id):
        return self.client.get(self.url("%s/tariff" % customer_id)).json["tariff_info"]

    def get_subscription(self, customer_id):
        return self.client.get(self.url("%s/subscribe" % customer_id)).json["subscribe"]

    def deferred(self, customer_id):
        return Deferred(self.client, str(customer_id))

    def update_balance(self, customer_id, amount, comment, currency=None):
        params = {"amount": amount, "comment": comment}
        if currency:
            params["currency"] = currency
        return self.client.put(self.url("%s/balance" % customer_id, ), params=params).json["customer_info"]

    def balance_history(self, customer_id, **kwargs):
        return self.client.get(self.url("%s/balance/history" % customer_id, ), params=kwargs).json["account_history"]

    def block(self, customer_id, blocked=True):
        return self.client.put(self.url("%s/block" % customer_id), params={"blocked": blocked}).json["customer_info"]

    def quota(self, customer_id):
        return QuotaCRUD(self.client, str(customer_id))

    def make_prod(self, customer_id):
        return self.client.post(self.url("%s/make_prod" % customer_id)).json[self.resource_info]

    def reset_password_valid(self, token):
        return self.client.get(self.url("password_reset/" + token), auth_required=False).json

    def reset_password(self, token, new_password):
        return self.client.post(self.url("password_reset/" + token),
                                params={"password": new_password},
                                auth_required=False).json

    def request_reset_password(self, email):
        return self.client.delete(self.url("password_reset"),
                                  params={"email": email},
                                  auth_required=False).json

    def history(self, customer_id, after=None, before=None, limit=None):
        params = {}
        if after:
            params["after"] = format_api_date(after)
        if before:
            params["before"] = format_api_date(before)
        if limit:
            params["limit"] = limit
        return self.client.get(self.url("%s/history" % customer_id), params=params).json["history"]

    def change_withdraw_period(self, customer_id, period):
        return self.client.post(self.url("%s/withdraw" % customer_id),
                                params={'period': period}).json[self.resource_info]

    def report(self, customer_id, start, finish, report_format="json", report_type="simple"):
        return self.client.post(self.url("%s/report" % customer_id),
                                params={"start": format_api_date_hour(start),
                                        "finish": format_api_date_hour(finish),
                                        "report_format": report_format,
                                        "report_type": report_type})

    def fake_usage(self, customer_id, start, finish, service_id, resource_id, volume):
        return self.client.post(self.url("%s/_fake_usage" % customer_id),
                                params={"start": format_api_date(start),
                                        "finish": format_api_date(finish),
                                        "service_id": service_id,
                                        "resource_id": resource_id,
                                        "volume": volume})

    def used_quotas(self, customer_id):
        return self.client.get(self.url("%s/used_quotas" % customer_id)).json

    def recreate_tenant(self, customer_id):
        return self.client.post(self.url("%s/recreate_tenant" % customer_id))

    def get_payment_cards(self):
        return self.client.get(self.url("payments/cloudpayments/card"))

    def delete_payment_card(self, card_id):
        return self.client.delete(self.url("payments/cloudpayments/card"), params={'card_id': card_id})

    def reset_os_password(self):
        return self.client.put(self.url("me/reset_os_password"))

    def auto_withdraw_change(self, enabled, balance_limit, payment_amount):
        return self.client.post(self.url("me/payments/auto_withdraw"),
                                params={'enabled': enabled,
                                        'balance_limit': balance_limit,
                                        'payment_amount': payment_amount})

    def auto_withdraw_get(self):
        return self.client.get(self.url("me/payments/auto_withdraw"))

    def withdraw_from_card(self, card_id, amount):
        params = {'card_id': card_id, 'amount': amount}
        return self.client.post(self.url("me/payments/withdraw"), params=params)

    def invoice(self, customer_id, ammount, date=None):
        return self.client.post(self.url("%s/invoice" % customer_id),
                                params={"amount": ammount,
                                        "date": date})

    def list(self, tariff_ids=None, created_before=None, created_after=None, **kwargs):
        if created_before:
            kwargs['created_before'] = format_api_date(created_before)
        if created_after:
            kwargs['created_after'] = format_api_date(created_after)
        if isinstance(tariff_ids, list):
            kwargs['tariff_ids'] = ','.join(tariff_ids)
        elif tariff_ids:
            kwargs['tariff_ids'] = tariff_ids
        res = self.client.get(self.url(), params=kwargs).json
        if self.resource_list:
            return res[self.resource_list]
        return res

    def group_update(self, customers, tariff=None, deferred_date=None, **kwargs):
        params = {"customers": ",".join(str(c) for c in customers)}
        if tariff:
            params["tariff"] = tariff
        if deferred_date:
            params["deferred_date"] = format_api_date(deferred_date)
        params.update(kwargs)
        return self.client.put(self.url("group"), params).json["customer_info"]


class TariffCRUD(BaseCRUD):
    resource_name = "tariff"
    resource_info = "tariff_info"

    def history(self, tariff_id, **kwargs):
        return self.client.get(self.url("%s/history" % tariff_id), params=kwargs).json["tariff_history"]

    def immutable(self, tariff_id):
        return self.client.put(self.url("%s/immutable" % tariff_id)).json["tariff_info"]

    def history_item(self, tariff_id, history_id):
        return self.client.get(self.url("%s/history/%s" % (tariff_id, history_id))).json["tariff_history_info"]

    def make_default(self, tariff_id):
        return self.client.put(self.url("%s/default" % tariff_id)).json["tariff_info"]

    def get_default(self):
        return self.get("default")

    def list(self, created_before=None, created_after=None,
             deleted_before=None, deleted_after=None, modified_before=None,
             modified_after=None, **kwargs):
        if created_before:
            kwargs['created_before'] = format_api_date(created_before)
        if created_after:
            kwargs['created_after'] = format_api_date(created_after)
        if deleted_before:
            kwargs['deleted_before'] = format_api_date(deleted_before)
        if deleted_after:
            kwargs['deleted_after'] = format_api_date(deleted_after)
        if modified_before:
            kwargs['modified_before'] = format_api_date(modified_before)
        if modified_after:
            kwargs['modified_after'] = format_api_date(modified_after)
        res = self.client.get(self.url(), params=kwargs).json
        if self.resource_list:
            return res[self.resource_list]
        return res


class NewsCRUD(BaseCRUD):
    resource_name = "news"
    resource_info = "news_info"

    def publish(self, news_id, publish):
        return self.client.post(self.url(news_id), params={"publish": publish}).json[self.resource_info]

    def list(self, published_before=None, published_after=None,
             deleted_before=None, deleted_after=None, **kwargs):
        if published_before:
            kwargs['published_before'] = format_api_date(published_before)
        if published_after:
            kwargs['published_after'] = format_api_date(published_after)
        if deleted_before:
            kwargs['deleted_before'] = format_api_date(deleted_before)
        if deleted_after:
            kwargs['deleted_after'] = format_api_date(deleted_after)
        res = self.client.get(self.url(), params=kwargs).json['news_list']
        return res


class PaymentsCRUD(BaseCRUD):
    prefix = "/api/0/payments"

    def cloudpayments_get_request_hmac(self, request_data):
        from api.admin.payments import PaymentsApi
        data_bytes = bytes(json.dumps(request_data), encoding="utf-8")
        return PaymentsApi.get_request_hmac(data_bytes, conf.payments.cloudpayments.api_secret)

    def cloudpayments_pay(self, request_data):
        request_headers = {
            # Auth header
            "Content-HMAC": self.cloudpayments_get_request_hmac(request_data)
        }
        res = self.client.post("%s/cloudpayments/pay/" % self.prefix,
                               params=request_data,
                               headers=request_headers,
                               as_json=True)
        return res

    def cloudpayments_check(self, request_data):
        request_headers = {
            # Auth header
            "Content-HMAC": self.cloudpayments_get_request_hmac(request_data)
        }
        res = self.client.post("%s/cloudpayments/check/" % self.prefix,
                               params=request_data,
                               headers=request_headers,
                               as_json=True)
        return res


class Report(BaseCRUD):
    resource_name = "report"

    def report(self, report_type, start, finish, report_format=None, locale=None):
        params = {"start": format_api_date_hour(start),
                  "finish": format_api_date_hour(finish),
                  "report_format": report_format}
        if locale:
            params["locale"] = locale
        return self.client.post(self.url(report_type), params=params)

    def receipts(self, start, finish, report_format, locale=None):
        return self.report("receipts", start, finish, report_format, locale)

    def usage(self, start, finish, report_format, locale=None):
        return self.report("usage", start, finish, report_format, locale)


class Statistics(BaseCRUD):
    resource_name = "stat"

    def stat_ips(self):
        return self.client.get(self.url("ips")).json

    def customers_stats(self):
        return self.client.post(self.url("customer")).json["customer_stats"]

    def openstack_usage(self, locale=None, format="json"):
        return self.client.post(self.url("openstack/usage"),
                                params=self.remove_none({"locale": locale, "format": format}))


class Graphite(BaseResourceApi):
    resource_name = "graphite"


class ApiClient(object):
    HTTP_OK = 200
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"

    def __init__(self, app, token_name):
        self.app = app
        self.token_name = token_name
        self.last_response = None

    def get(self, url, params=None, headers=None, auth_required=True):
        return self._send("GET", url, params, headers, auth_required)

    def post(self, url, params=None, headers=None, auth_required=True, upload_files=None, as_json=False):
        return self._send("POST", url, params, headers, auth_required, upload_files=upload_files, as_json=as_json)

    def delete(self, url, params=None, headers=None, auth_required=True):
        return self._send("DELETE", url, params, headers, auth_required)

    def put(self, url, params=None, headers=None, auth_required=True, as_json=False):
        return self._send("PUT", url, params, headers, auth_required, as_json=as_json)

    def options(self, url, headers=None):
        return self._send("OPTIONS", url, None, headers, auth_required=False)

    def auth(self, *args, **kwargs):
        raise NotImplemented()

    def logout(self, *args, **kwargs):
        raise NotImplemented()

    def _send(self, method, url, params=None, headers=None, auth_required=True, as_json=False, upload_files=None):
        if params is None:
            params = {}
        if not as_json:
            params = self.prepare_params(params)

        if auth_required:
            if self.token_name not in self.app.cookies:
                self.auth()

        bot_secret = params.pop("bot_secret", None)
        if bot_secret:
            from boss_client.auth import Signature
            signature = Signature(conf.api.secure.secret_key)
            sign = signature.calculate_signature(time.time(), method, url, params)
            params["bot_secret"] = sign

        if method == self.DELETE and params is not None:
            import urllib.parse

            url += "?" + urllib.parse.urlencode(params)
            params = ""
        kwargs = {"upload_files": upload_files} if upload_files else {}

        if headers is None:
            headers = {}

        if method.lower() == "options":
            res = self.app.options(url=url, headers=headers, expect_errors=True, **kwargs)
        else:
            if as_json:
                method += "_json"
            method = getattr(self.app, method.lower())
            res = method(url=url, params=params, headers=headers, expect_errors=True, **kwargs)
            self.last_response = res
        if 200 <= res.status_int < 400:
            return res

        raise ResponseError(res)

    @staticmethod
    def prepare_params(params):
        """
        Convert values and keys to utf-8
        :param dict params: incoming dictionary with parameters
        """

        def convert(v):
            if isinstance(v, str):
                return v
            return str(v)

        return {convert(k): convert(v) for k, v in params.items()}


class ApiAdminClient(ApiClient):
    def __init__(self, app, email, password):
        super().__init__(app, "token")
        self.email = email
        self.password = password
        self.user = UserCRUD(self)
        self.service = ServiceCRUD(self)
        self.currency = Currency(self)
        self.tariff = TariffCRUD(self)
        self.news = NewsCRUD(self)
        self.customer = CustomerCRUD(self)
        self.payments = PaymentsCRUD(self)
        self.customer.prefix = "/api/0/"
        self.report = Report(self)
        self.stats = Statistics(self)
        self.graphite = Graphite(self)

    def auth(self, email=None, password=None, return_user_info=False):
        params = {"password": password or self.password, "email": email or self.email,
                  "return_user_info": return_user_info}
        return self.post('/api/0/auth/', params, auth_required=False).json["user_info"]

    def logout(self):
        return self.post('/api/0/logout')

    def version(self):
        return self.get('/api/version').json


class ApiCabinetClient(ApiClient):
    def __init__(self, app):
        super().__init__(app, "cabinet_token")
        self.customer = CustomerCRUD(self)

    def auth(self, email, password, return_customer_info=False):
        params = locals()
        del params['self']
        return self.post('/lk_api/0/auth/', params, auth_required=False).json['customer_info']

    def logout(self):
        return self.post('/lk_api/0/logout/')


class OpenstackUser:
    id = '1'
    enabled = True

    def __init__(self, name, email, tenant_id, **kwargs):
        self.name = name
        self.username = name
        self.email = email
        self.tenantId = tenant_id


class OpenstackTenant:
    id = '1'
    name = 'TestTenant'


class TestCaseApi(BaseTestCaseDB):

    HTTP_OK = 200
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
    user_count = 0

    def get_app(self, api_type):
        import view
        view_app = view.api_handler(api_type)
        return TestApp(view_app, extra_environ={"REMOTE_ADDR": "8.8.8.8"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # from fixtures
        self.email = "boss@yourstack.com"
        self.password = "qscft"
        self.admin_client = None
        self.cabinet_client = None

    def setUp(self):
        # openstack.create_tenant_and_user = mock.MagicMock()
        # openstack_task.task_os_create_tenant_and_user = mock.MagicMock()

        super().setUp()
        self.admin_client = ApiAdminClient(self.get_app(API_ADMIN), self.email, self.password)
        self.cabinet_client = ApiCabinetClient(self.get_app(API_CABINET))

    @contextlib.contextmanager
    def expect_error(self, error):
        try:
            yield
        except ResponseError as e:
            if e.response.status_int != error.default_status:
                raise
        else:
            raise Exception("Exception {} was not raised".format(error))

    def extract_services(self, services):
        return [{"price": service_price["price"],
                 "service_id": service_price["service"]["service_id"]} for service_price in services]

    def new_customer_info(self, email, **kwargs):
        info = {"email": email, "password": email}
        info.update(kwargs)
        return info

    def create_customer_by_self(self, email, auth=True, **kwargs):
        info = self.new_customer_info(email, **kwargs)
        customer_info = self.cabinet_client.customer.create(**info)
        if auth:
            self.cabinet_client.auth(info["email"], info["password"])
        customer_info["password"] = info["password"]
        return customer_info

    def create_customer(self, email, **kwargs):
        info = self.new_customer_info(email, **kwargs)
        customer_info = self.admin_client.customer.create(**info)
        customer_info["password"] = info["password"]
        return customer_info

    def create_tariff(self, name, immutable=True, default=False, **kwargs):
        data = {"localized_name": self.localized_name(name),
                "description": "Very expencive tariff %s" % name,
                "currency": "RUB",
                "services": [
                    {"service_id": "storage.Image", "price": "33.33"},
                    {"service_id": self.service_nano_id, "price": "2.23"}, # Nano
                    {"service_id": self.service_micro_id, "price": "1.23"}, # Micro
                    {"service_id": self.service_small_id, "price": "12.23"}, # Small
                    {"service_id": self.service_medium_id, "price": "23.45"}, # Medium
                    {"service_id": "net.fixed_ip", "price": "33.45"},
                    {"service_id": "net.allocated_ip", "price": "43.45"}]
                }
        tariff = self.admin_client.tariff.create(as_json=True, **data)
        if immutable:
            tariff = self.admin_client.tariff.immutable(tariff["tariff_id"])
            if default:
                tariff = self.admin_client.tariff.make_default(tariff["tariff_id"])
        return tariff


class FitterTestBase(BaseTestCaseDB):
    def setUp(self):
        super().setUp()
        self.objects = []
        self.called_replacement_resources = False
        self.end = datetime.datetime.utcnow()
        self.start = self.end - datetime.timedelta(days=30)
