import datetime
from pprint import pformat
from keystoneclient.access import AccessInfo
import logbook as logbook
from requests import HTTPError

from api_tests.cabinet_backend import CabinetBackendTestCase
from clients import OpenstackClient
import configs
import unittest
import entities
from utils.tools import format_backend_datetime


class EmailCustomerTests(CabinetBackendTestCase):
    def test_customer_email_confirm(self):
        self.cleanup_mailtrap(delayed=True)

        email = self.generate_mailtrap_email()
        customer_info, _, customer_client = self.create_customer(create_default_tariff=True, email=email,
                                                                 with_client=True)
        self.assertFalse(customer_info['email_confirmed'])
        self.confirm_customer(customer_info['email'], customer_client)
        customer_info = customer_client.customer.get()
        self.assertTrue(customer_info['email_confirmed'])

    def test_customer_password_reset(self):
        self.cleanup_mailtrap(delayed=True)

        email = self.generate_mailtrap_email()

        customer_info, _, customer_client = self.create_customer(create_default_tariff=True, email=email,
                                                                 with_client=True)

        customer_client.customer.send_password_reset(email)
        match = self.search_email(r'set-password/(?P<token>\w+)')
        token = match.group('token')

        customer_client.customer.validate_password_reset(token)

        new_password = self.generate_password()
        customer_client.customer.password_reset(token, new_password)

        with self.assertRaisesHTTPError(401):
            customer_client.customer.get()

        customer_client.login(customer_info['email'], new_password)


class CustomerSimpleTests(CabinetBackendTestCase):
    @unittest.skipIf(not configs.api.get('secure', {}).get('recaptcha', {}).get('validate', False),
                     'Recaptcha validation is disabled')
    def test_customer_without_botsecret(self):
        with self.assertRaisesHTTPError(401):
            customer_info, _ = self.create_customer(True, bot_secret=False)

    def test_customer_creation_by_admin_go_prod_with_no_info(self):
        with self.assertRaisesHTTPError(400):
            self.create_customer(True, by_admin=True, make_prod=True, customer_type='entity')

    def test_customer_creation_by_admin(self):
        customer_info, _, customer_client = self.create_customer(True, by_admin=True, with_client=True)
        self.assertEqual(customer_info['account']['RUB']['balance'], '200.00')

        customer_client.logout()

        with self.assertRaisesHTTPError(401):
            customer_client.customer.get()

    def test_customer_options(self):
        self.default_admin_client.customer.options()
        self.assertTrue("Content-Type" in self.default_admin_client.last.headers)
        self.assertEqual(self.default_admin_client.last.headers['Content-Type'], "text/html")
        self.assertTrue("Access-Control-Allow-Methods" in self.default_admin_client.last.headers)
        self.assertEqual(self.default_admin_client.last.headers["Access-Control-Allow-Methods"], "POST, OPTIONS")

    def test_customer_login_options(self):
        client = self.get_cabinet_client()
        client.login_options()
        self.assertTrue("Content-Type" in client.last.headers)
        self.assertEqual(client.last.headers['Content-Type'], "text/html")
        self.assertTrue("Access-Control-Allow-Methods" in client.last.headers)
        self.assertEqual(client.last.headers["Access-Control-Allow-Methods"], "POST, OPTIONS")

    def test_customer_update_in_prod(self):
        customer_info, _, customer_client = self.create_customer(True, by_admin=True, individual=True, with_client=True,
                                                                 make_prod=True)

        with self.assertRaisesHTTPError(400):
            customer_client.customer.update(detailed_info={'city': 'Orenburg'})

    def test_customer_email_confirmation_self(self):
        customer_info, _, customer_client = self.create_customer(True, with_client=True, mailtrap_email=True)
        self.search_email(r'confirmation/(?P<token>\w+)')
        self.cleanup_mailtrap()
        customer_client.customer.send_confirm_email()
        self.confirm_customer(customer_info['email'], customer_client)

        with self.assertRaisesHTTPError(400):
            customer_client.customer.os_login()

        self.wait_openstack(customer_info['customer_id'], delayed=True)
        self.assertTrue(customer_client.customer.get()['email_confirmed'])

    def test_customer_email_confirmation_by_admin(self):
        customer_info, _, customer_client = self.create_customer(True, with_client=True, mailtrap_email=True)
        self.search_email(r'confirmation/(?P<token>\w+)')
        self.cleanup_mailtrap()
        self.default_admin_client.customer.send_confirm_email(customer_info['customer_id'])
        self.confirm_customer(customer_info['email'], customer_client)
        self.wait_openstack(customer_info['customer_id'], delayed=True)
        self.assertTrue(customer_client.customer.get()['email_confirmed'])

    def test_customer_invoice(self):
        customer_info, _, customer_client = self.create_customer(True, entity=True, with_client=True, make_prod=True,
                                                                 customer_type='entity', by_admin=True)
        amount = 100
        invoice = customer_client.customer.invoice(amount)
        self.assertTrue(isinstance(invoice, bytes))

        invoice_admin = self.default_admin_client.customer.invoice(customer_info['customer_id'], amount)
        self.assertTrue(isinstance(invoice_admin, bytes))

    def test_invalid_customer_login(self):
        with self.assertRaisesHTTPError(401):
            self.get_cabinet_client('fake_email@example.com', 'password')

        customer_info, customer_credentials = self.create_customer(True)

        with self.assertRaisesHTTPError(401):
            self.get_cabinet_client(customer_credentials['email'], customer_credentials['password'] + 'hello')

        self.default_admin_client.customer.delete(customer_info['customer_id'])

        with self.assertRaisesHTTPError(401):
            self.get_cabinet_client(customer_credentials['email'], customer_credentials['password'])

    def test_customer_list(self):
        self.restore_default_tariff()

        visible_customer_tariff = self.create_tariff(set_default=True, immutable=True)

        customer_info, _ = self.create_customer()

        deleted_customer_tariff = self.create_tariff(set_default=True, immutable=True)
        customer_info_deleted, _ = self.create_customer(True)
        self.default_admin_client.customer.delete(customer_info_deleted['customer_id'])

        customer_in_list = lambda customer_list, customer_info: self.assertInList(customer_list, lambda customer: customer['customer_id'] == customer_info['customer_id'])

        customer_list_visible = self.default_admin_client.customer.list(visibility='visible')['items']
        customer_in_list(customer_list_visible, customer_info)
        with self.assertRaises(AssertionError):
            customer_in_list(customer_list_visible, customer_info_deleted)

        customer_list_deleted = self.default_admin_client.customer.list(visibility='deleted')['items']
        customer_in_list(customer_list_deleted, customer_info_deleted)
        with self.assertRaises(AssertionError):
            customer_in_list(customer_list_deleted, customer_info)

        customer_list_all = self.default_admin_client.customer.list(visibility='all')['items']
        customer_in_list(customer_list_all, customer_info)
        customer_in_list(customer_list_all, customer_info_deleted)

        customer_list_by_all_tariffs = self.default_admin_client.customer.list(visibility='all',
            tariff_ids=','.join(map(str, [visible_customer_tariff['tariff_id'], deleted_customer_tariff['tariff_id']])))['items']
        customer_in_list(customer_list_by_all_tariffs, customer_info)
        customer_in_list(customer_list_by_all_tariffs, customer_info_deleted)

        customer_list_by_visible_tariff = self.default_admin_client.customer.list(visibility='all',
            tariff_ids=str(visible_customer_tariff['tariff_id']))['items']
        customer_in_list(customer_list_by_visible_tariff, customer_info)
        with self.assertRaises(AssertionError):
            customer_in_list(customer_list_by_visible_tariff, customer_info_deleted)

        customer_list_by_deleted_tariff = self.default_admin_client.customer.list(visibility='all',
            tariff_ids=str(deleted_customer_tariff['tariff_id']))['items']
        customer_in_list(customer_list_by_deleted_tariff, customer_info_deleted)
        with self.assertRaises(AssertionError):
            customer_in_list(customer_list_by_deleted_tariff, customer_info)

class CustomerSelfTests(CabinetBackendTestCase):
    def setUp(self):
        super().setUp()
        self.default_tariff = self.get_or_create_default_tariff()[0]
        self.customer, _, self.customer_client = self.create_customer(with_client=True)

    def search_customer_in_list(self, customer_list:list, customer_id:int):
        for custmer in customer_list:
            if customer_id == custmer['customer_id']:
                break
        else:
            self.fail('Customer {} not found in customer list'.format(customer_id))

    def test_customer_in_list(self):
        customer_list = self.default_admin_client.customer.list()
        self.search_customer_in_list(customer_list['items'], self.customer['customer_id'])

        customer_list = self.default_admin_client.customer.list(email=self.customer['email'])
        self.search_customer_in_list(customer_list['items'], self.customer['customer_id'])

        customer_list = self.default_admin_client.customer.list(name=self.customer['detailed_info']['name'])
        self.search_customer_in_list(customer_list['items'], self.customer['customer_id'])

    def test_customer_tariff(self):
        tariff = self.default_admin_client.customer.tariff.get(self.customer['customer_id'])
        self.assertEqual(tariff['tariff_id'], self.default_tariff['tariff_id'])

        tariff = self.customer_client.customer.tariff.get()
        self.assertDictEqual(tariff['localized_name'], self.default_tariff['localized_name'])

    def test_customer_update(self):
        with self.assertRaisesHTTPError(400):
            self.customer_client.customer.update()

        with self.assertRaisesHTTPError(400):
            self.default_admin_client.customer.update(self.customer['customer_id'])

        new_phone = 'New Phone'
        customer_info = self.customer_client.customer.update(detailed_info=dict(telephone=new_phone))
        self.assertEqual(customer_info['detailed_info']['telephone'], new_phone)

        customer_info = self.customer_client.customer.get()
        self.assertEqual(customer_info['detailed_info']['telephone'], new_phone)

    def test_customer_password_update(self):
        new_password = self.generate_password()
        self.customer = self.customer_client.customer.update(password=new_password)

        self.customer_client.login(self.customer['email'], new_password)

    def test_customer_subscribitions_list(self):
        subscribe = self.customer_client.customer.subscription.get()
        self.assertGreater(len(subscribe), 0)

    def test_customer_subscribitions_update(self):
        old_subscribe = self.customer_client.customer.subscription.get()
        self.customer_client.customer.subscription.update({'news':{'enable': not old_subscribe['news']['enable'], 'email':[]}})
        subscribe = self.customer_client.customer.subscription.get()
        self.assertNotEqual(subscribe['news']['enable'], old_subscribe['news']['enable'])

    def test_getting_quotas(self):
        quotas = self.customer_client.customer.quota()
        self.assertGreater(len(quotas), 0)
        for quota in quotas:
            self.assertIn('limit_id', quota)
            self.assertIn('localized_description', quota)
            self.assertIn('value', quota)

    def test_customer_cant_go_production(self):
        self.assertFalse(self.customer['email_confirmed'])
        with self.assertRaisesHTTPError(409):
            self.customer_client.customer.make_prod()

    def test_customer_account_history(self):
        history = self.customer_client.customer.balance_history()
        self.assertGreater(len(history), 0)
        for item in history:
            if item['comment'] == 'Initial test balance':
                break
        else:
            self.fail('"Initial test balance" not found in account history:'+str(history))

    def test_horizon_auth(self):
        with self.assertRaisesHTTPError(409):
            self.customer_client.customer.os_login()

    def test_used_quotas(self):
        for r in self.retries(10, exception=HTTPError):
            with r:
                used_quotas = self.customer_client.customer.quota_used()['used_quotas']
                self.assertEqual(len(used_quotas), 0)

    def test_recreate_tenant(self):
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.customer.recreate_tenant(self.customer['customer_id'])

    def test_customer_autowithdraw(self):
        settings = self.customer_client.customer.auto_withdraw.get()
        settings_admin = self.default_admin_client.customer.auto_withdraw.get(self.customer['customer_id'])
        self.assertDictEqual(settings, settings_admin)

        self.customer_client.customer.auto_withdraw.update(enabled=not settings['enabled'])
        settings = self.customer_client.customer.auto_withdraw.get()
        self.assertEqual(settings['enabled'], not settings_admin['enabled'])

        self.default_admin_client.customer.auto_withdraw.update(self.customer['customer_id'], enabled=not settings['enabled'])

    def test_customer_report(self):
        def make_report_datetime(dt: datetime.datetime):
            return format_backend_datetime(dt, time_format='%H')

        finish_dt = datetime.datetime.now() - datetime.timedelta(days=1)
        start_dt = finish_dt - datetime.timedelta(days=1)
        finish = make_report_datetime(finish_dt)
        start = make_report_datetime(start_dt)
        with self.assertRaisesHTTPError(409):
            self.customer_client.customer.report(start, finish, 'json')


class OpenstackCustomerTests(CabinetBackendTestCase):
    def setUp(self):
        super().setUp()
        self.customer_info, _, self.customer_client = self.create_customer(create_default_tariff=True, confirmed=True,
                                                                           need_openstack=True, with_client=True)

    @unittest.skip('')
    def test_openstack_access(self):
        self.assertTrue(self.customer_info['email_confirmed'])
        self.customer_client.customer.os_login()
        self.assertIn('sessionid', self.customer_client.session.cookies)

        for r in self.retries(120):
            with r:
                used_quotas = self.customer_client.customer.quota_used()['used_quotas']
                self.assertEqual(len(used_quotas), 3)

    def test_openstack_auth(self):
        token_info = self.customer_client.customer.get_openstack_auth()
        openstack_client = OpenstackClient.init_by_token(token_info)
        image_list = openstack_client.image_list()
        # TODO: how to test this?

class CustomerProductionTest(CabinetBackendTestCase):
    individual = True
    entity = False
    balance_amount = 256
    default_balance = 200

    def test_customer_goes_prod(self):
        self.customer, _, self.customer_client = self.create_customer(create_default_tariff=True, confirmed=True,
                                                                      individual=self.individual, entity=self.entity,
                                                                      with_client=True, go_prod=True, mailtrap_email=True)
        self.customer = self.default_admin_client.customer.update_balance(self.customer['customer_id'], self.balance_amount, 'Hello, world!')

        self.assertIn(str(self.balance_amount+self.default_balance), self.customer['account']['RUB']['balance'])
        self.assertEqual(self.customer['customer_mode'], 'production')

        self.search_email(r'(Ваш аккаунт был переведен в Продуктовый режим!)|(Your account has been changed to Production mode!)')

        self.customer = self.customer_client.customer.make_prod()
        self.assertEqual(self.customer['customer_mode'], 'production')

        self.customer = self.default_admin_client.customer.make_prod(self.customer['customer_id'])
        self.assertEqual(self.customer['customer_mode'], 'production')

    def test_customer_goes_prod_by_admin(self):
        self.customer, _, self.customer_client = self.create_customer(True, confirmed=True, with_client=True,
                                                                      by_admin=True, customer_type='entity',
                                                                      mailtrap_email=True)
        with self.assertRaisesHTTPError(400):
            self.default_admin_client.customer.make_prod(self.customer['customer_id'])

        with self.assertRaisesHTTPError(400):
            self.customer_client.customer.make_prod()

        entity_info = entities.CustomerCredentials(self).generate_entity_fields()
        self.default_admin_client.customer.update(self.customer['customer_id'], detailed_info=entity_info)

        self.default_admin_client.customer.make_prod(self.customer['customer_id'])

        self.customer = self.default_admin_client.customer.update_balance(self.customer['customer_id'], self.balance_amount, 'Hello, world!')

        self.assertIn(str(self.balance_amount+self.default_balance), self.customer['account']['RUB']['balance'])
        self.assertEqual(self.customer['customer_mode'], 'production')

        self.search_email(r'(Ваш аккаунт был переведен в Продуктовый режим!)|(Your account has been changed to Production mode!)')


@unittest.skipIf(getattr(configs.devel, 'local', False), 'Cant assing local cookies due to BOSS-1196')
class TestCustomerOSPasswordReset(CabinetBackendTestCase):
    def test_customer_reset_os_password(self):
        customer, _, customer_client = self.create_customer(True, individual=True, with_client=True, mailtrap_email=True)

        with self.assertRaisesHTTPError(400):
            customer_client.customer.reset_os_password()

        self.confirm_customer(customer['email'], customer_client)
        self.wait_openstack(customer['customer_id'])

        self.default_admin_client.customer.block(customer['customer_id'], True)

        for r in self.retries():
            with r:
                with self.assertRaisesHTTPError(409):
                    customer_client.customer.reset_os_password()

        self.default_admin_client.customer.block(customer['customer_id'], False)

        for r in self.retries(10, exception=HTTPError):
            with r:
                customer_client.customer.os_login()

        customer_client.customer.reset_os_password()

        for r in self.retries(30, exception=HTTPError):
            with r:
                customer_client.customer.os_login()

        self.check_horizon(customer_client)


@unittest.skipIf(not configs.promocodes.promo_registration_only, 'Promocodes are disabled')
class TestPromocodeRegistration(CabinetBackendTestCase):
    def test_promocode_error(self):
        with self.assertRaisesHTTPError(400):
            self.create_customer(True, with_promocode=False)

        with self.assertRaisesHTTPError(401):
            self.create_customer(True, with_promocode=False, promo_code='invalidpromocode')

    def test_promocode_customer_creation(self):
        customer, _, customer_client = self.create_customer(True, with_client=True)
        self.assertEqual(customer['promo_code'][0]['value'], self.get_default_promocode())
