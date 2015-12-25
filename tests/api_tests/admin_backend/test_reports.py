import datetime
import logbook
import random
import csv
import io

from api_tests.admin_backend import AdminBackendTestCase
from utils.tools import format_backend_datetime
from clients import OpenstackClient
import keystoneclient.exceptions


CONTENT_TYPES = {"pdf": "application/pdf",
                 "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 "json": "application/json",
                 "csv": "text/csv"}


class ReportsTestsBase(AdminBackendTestCase):
    report_time_format = '%H'

    @classmethod
    def make_report_datetime(cls, dt: datetime.datetime):
        return format_backend_datetime(dt, time_format=cls.report_time_format)


class CustomerReportsTests(ReportsTestsBase):
    service_id = None
    resource_id = 'disk1'
    volume = 1245

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.finish_dt = datetime.datetime.now() - datetime.timedelta(days=1)
        cls.start_dt = cls.finish_dt - datetime.timedelta(days=1)
        cls.finish = cls.make_report_datetime(cls.finish_dt)
        cls.start = cls.make_report_datetime(cls.start_dt)

        cls.service_id = next(cls.get_immutable_services())

    def setUp(self):
        super().setUp()
        self.tariff = None
        existed_default_tariff = self.check_default_tariff()
        if not existed_default_tariff:
            self.tariff = self.create_tariff([(self.service_id, '123')], set_default=True, immutable=True)
            self.addCleanupBeforeDelete(self.default_admin_client.tariff.set_default, existed_default_tariff['tariff_id'])
        else:
            if existed_default_tariff['services']:
                self.service_id = existed_default_tariff['services'][0]['service']['service_id']
            else:
                self.tariff = self.create_tariff([(self.service_id, '123')], set_default=True, immutable=True)
                self.addCleanupBeforeDelete(self.default_admin_client.tariff.set_default, existed_default_tariff['tariff_id'])
        self.customer, _, self.customer_client = self.create_customer(confirmed=True, with_client=True, need_openstack=True)
        self.generate_fake_data()

    def generate_fake_data(self):
        resource_id = 'disk1'
        volume = 1245
        self.default_admin_client.customer.fake_usage(self.customer['customer_id'],
                                                      self.make_datetime(self.start_dt),
                                                      self.make_datetime(self.finish_dt),
                                                      self.service_id, resource_id, volume)

    def get_report(self, report_format, start=None, finish=None, cabinet_api:bool=False, report_type=None):
        if start is None:
            start = self.start
        elif isinstance(start, datetime.datetime):
            start = self.make_report_datetime(start)
        if finish is None:
            finish = self.finish
        elif isinstance(finish, datetime.datetime):
            finish = self.make_report_datetime(finish)
        if not cabinet_api:
            return self.default_admin_client.customer.report(self.customer['customer_id'], start, finish, report_format, report_type)
        else:
            return self.customer_client.customer.report(start, finish, report_format, report_type)

    def wait_report(self, report_format, start=None, finish=None, cabinet_api:bool=False, report_type=None):
        for r in self.retries(20):
            with r:
                report = self.get_report(report_format, start, finish, cabinet_api, report_type)
                if cabinet_api:
                    last = self.customer_client.last
                else:
                    last = self.default_admin_client.last
                if isinstance(report, dict):
                    self.assertEqual(report['status'], 'completed')
                self.assertIn(CONTENT_TYPES[report_format], last.headers['content-type'])
        return report

    def test_cabinet_admin_reports_identical(self):
        cabinet_report = self.wait_report('json', cabinet_api=True)
        admin_report = self.wait_report('json')
        self.assertDictEqual(cabinet_report['report'], admin_report['report'])

    def test_reports_errors(self):
        future_start = datetime.datetime.now() + datetime.timedelta(days=7)
        future_finish = future_start + datetime.timedelta(days=7)

        with self.assertRaisesHTTPError(400):
            self.get_report('json', future_start, future_finish)

        with self.assertRaisesHTTPError(400):
            self.get_report('json', self.finish, self.start)

        with self.assertRaisesHTTPError(409):
            self.get_report('json', self.start, self.finish, report_type='acceptance_act')

    def test_customer_reports(self):
        report = self.wait_report('json')
        self.assertIn('report', report)

        report = self.wait_report('csv')
        self.assertIsInstance(report, bytes)


class AdminReportsTests(ReportsTestsBase):
    to_prod_balance = 123
    to_prod_comment = 'Going to prod'
    after_prod_balance = 234
    after_prod_comment = 'Balance update in production'
    _offsets = set()

    def generate_time_interval(self, offset:int=None) -> tuple:
        if offset is None:
            while True:
                offset = random.randint(2, 24)
                if offset in self._offsets:
                    continue
                self._offsets.add(offset)
                break

        finish_dt = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        start_dt = finish_dt - datetime.timedelta(hours=offset)
        finish = self.make_report_datetime(finish_dt)
        start = self.make_report_datetime(start_dt)
        return start, finish

    def setUp(self):
        super().setUp()

        self.customer, _ = self.create_customer(True, confirmed=True, individual=True, go_prod=True, need_openstack=True)
        self.default_admin_client.customer.update_balance(self.customer['customer_id'], self.to_prod_balance, self.to_prod_comment)
        self.default_admin_client.customer.update_balance(self.customer['customer_id'], self.after_prod_balance, self.after_prod_comment)

    def test_receipts(self):
        start, finish = self.generate_time_interval()

        with self.assertRaisesHTTPError(400):
            self.default_admin_client.reports.receipts(finish, start, report_format='csv')

        while True:
            report = self.default_admin_client.reports.receipts(start, finish, report_format='csv', locale='en')
            if isinstance(report, bytes):
                start, finish = self.generate_time_interval()
                continue
            break

        report = self.wait_report('csv', start, finish)

        last = self.default_admin_client.last
        self.assertIn(CONTENT_TYPES['csv'], last.headers['content-type'])

        report = self.from_csv_to_dict(report)
        report = list(filter(lambda r: r['email'] == self.customer['email'], report))

        self.search_in_report(self.to_prod_comment, self.to_prod_balance, report)
        self.search_in_report(self.after_prod_comment, self.after_prod_balance, report)

    def from_csv_to_dict(self, raw_bytes_report) -> list:
        report = csv.DictReader(io.StringIO(raw_bytes_report.decode()))
        return [{k.lower(): v for k, v in r.items()} for r in report]

    def search_in_report(self, comment, amount, report):
        for r in report:
            if str(amount) in r['amount']:
                return r
        self.fail('Did not found ({}, {}) in report {}'.format(comment, amount, report))

    def wait_report(self, type, start=None, finish=None):
        for r in self.retries(20):
            with r:
                report = self.default_admin_client.reports.receipts(start, finish, report_format=type, locale='en')
                self.assertTrue(isinstance(report, bytes))
        return report


class StatisticsTests(AdminBackendTestCase):
    maxDiff = None

    def test_customer_stats(self):
        get_stats = lambda: self.default_admin_client.stats.customer()
        stats = get_stats()

        # create test private
        customer_info, _, customer_client = self.create_customer(True, confirmed=True, with_client=True, individual=True, need_openstack=True)
        stats['total'] += 1
        stats['total_test'] += 1
        stats['test_private'] += 1
        self.assertDictEqual(stats, get_stats())
        stats = get_stats()

        # block test private
        self.default_admin_client.customer.block(customer_info['customer_id'], True)
        stats['test_private_blocked'] += 1
        stats['total_blocked'] += 1
        self.assertDictEqual(stats, get_stats())
        self.default_admin_client.customer.block(customer_info['customer_id'], False)
        stats = get_stats()

        # make pending prod private
        new_balance = float(customer_info['balance_limit']) - float(customer_info['account']['RUB']['balance'])
        self.default_admin_client.customer.update_balance(customer_info['customer_id'], new_balance, 'balance update')
        customer_client.customer.make_prod()
        stats['pending_prod_private'] += 1
        stats['total_pending_prod'] += 1
        stats['test_private'] -= 1
        stats['total_test'] -= 1
        self.assertDictEqual(stats, get_stats())
        stats = get_stats()

        # block pending prod private
        self.default_admin_client.customer.block(customer_info['customer_id'], True)
        stats['pending_prod_private_blocked'] += 1
        stats['total_blocked'] += 1
        self.assertDictEqual(stats, get_stats())
        self.default_admin_client.customer.block(customer_info['customer_id'], False)
        stats = get_stats()

        # make prod private
        self.default_admin_client.customer.update_balance(customer_info['customer_id'], float(customer_info['balance_limit'])+1, 'balance update')
        stats['production_private'] += 1
        stats['total_production'] += 1
        stats['pending_prod_private'] -= 1
        stats['total_pending_prod'] -= 1
        self.assertDictEqual(stats, get_stats())
        stats = get_stats()

        # block prod private
        self.default_admin_client.customer.block(customer_info['customer_id'], True)
        stats['total_blocked'] += 1
        stats['production_private_blocked'] += 1
        self.assertDictEqual(stats, get_stats())
        self.default_admin_client.customer.block(customer_info['customer_id'], True)
        stats = get_stats()

        # delete prod private
        self.default_admin_client.customer.delete(customer_info['customer_id'])
        stats['total_deleted'] += 1
        stats['private_deleted'] += 1
        self.assertDictEqual(stats, get_stats())

    def get_used_quotas(self, customer_client) -> dict:
        """Return formatted used_quotas dict"""
        for r in self.retries(20, 1):
            with r:
                used_quotas = customer_client.customer.quota_used()
                self.assertFalse(used_quotas['loading'])
                used_quotas = used_quotas['used_quotas']

        result = dict()
        for section_dict in used_quotas:
            for section_name, section_info in section_dict.items():
                for quote_info in section_info:
                    result[quote_info['limit_id']] = quote_info
        return result

    def test_ips_stats(self):
        customer_info, _, customer_client = self.create_customer(True, confirmed=True, with_client=True, individual=True,
                                                                 need_openstack=True, mailtrap_email=True)
        openstack_credentials = self.get_openstack_credentials(customer_info)
        openstack_client = OpenstackClient.init_by_creds(*openstack_credentials)

        quotas = self.get_used_quotas(customer_client)
        if quotas['floatingip']['max_value'] < 2:
            self.default_admin_client.customer.quota.update(customer_info['customer_id'], {'floatingip': 2})
        quotas = self.get_used_quotas(customer_client)
        self.assertEqual(quotas['floatingip']['max_value'], 2)

        for r in self.retries(30, 1):
            with r:
                quota = openstack_client.neutron_client.show_quota(openstack_credentials[0])['quota']
                self.assertEqual(quota['floatingip'], 2)

        get_stats = lambda: self.default_admin_client.stats.ips()

        def inc(d:dict, key:str):
            if key not in d:
                d[key] = 0
            d[key] += 1

        def dec(d:dict, key:str):
            d[key] -= 1
            if d[key] == 0:
                d.pop(key)

        stats = get_stats()

        floating_ip = openstack_client.nova_client.floating_ips.create(openstack_client.nova_client.floating_ip_pools.list()[0].name)
        self.addCleanupBeforeDelete(floating_ip.delete)

        inc(stats, 'active_customer')
        inc(stats, 'customer_mode-test')
        inc(stats, 'customer_type-private')
        inc(stats, 'total')
        inc(stats, 'ip_status-DOWN')
        for r in self.retries(10, 1):
            with r:
                self.assertDictEqual(stats, get_stats())

        # block test private
        self.default_admin_client.customer.block(customer_info['customer_id'], True)
        inc(stats, 'blocked_customer')
        dec(stats, 'active_customer')
        for r in self.retries(10, 1):
            with r:
                self.assertDictEqual(stats, get_stats())

        self.default_admin_client.customer.block(customer_info['customer_id'], False)
        stats = get_stats()

        # make prod private
        customer_client.customer.make_prod()
        inc(stats, 'customer_mode-production')
        dec(stats, 'customer_mode-test')
        for r in self.retries(10, 1):
            with r:
                self.assertDictEqual(stats, get_stats())

        # wait for customer unblocking task completed
        for r in self.retries(30, 1, keystoneclient.exceptions.Unauthorized):
            with r:
                openstack_client.keystone_client.get_raw_token_from_identity_service(
                    username=openstack_credentials.username,
                    tenant_id=openstack_credentials.tenant_id,
                    password=openstack_credentials.password,
                    auth_url=openstack_credentials.auth_url)
