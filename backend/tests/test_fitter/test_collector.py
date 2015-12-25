import datetime
import asyncio
import mock
import tempfile
import os
import conf

from decimal import Decimal
from tests.base import TestCaseApi
from tests.test_fitter.openstack_services import Tenant, Disk, Volume, Instance
from model import db, Customer, Tariff
from fitter.aggregation.collector import Collector
from utils.money import decimal_to_string
from utils.mail import outbox
from os_interfaces.openstack_wrapper import openstack


class TestCollector(TestCaseApi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        openstack.get_nova_flavor = mock.MagicMock(side_effect=cls.create_flavor_mock)

    def setUp(self):
        super().setUp()
        self.collector = Collector()
        self.image_size_price = "12.34"
        self.volume_size_price = "12.37"
        self.root_disk_price = "2.91"
        self.nano_price = "3.47"
        services = [{"service_id": "storage.image", "price": self.image_size_price},
                    {"service_id": "storage.volume", "price": self.volume_size_price},
                    {"service_id": "storage.disk", "price": self.root_disk_price},
                    {"service_id": self.service_nano_id, "price": self.nano_price}
                    ]
        self.tariff = Tariff.create_tariff(self.localized_name("Tariff for customers"), "tariff!!!", "rub",
                                           services=services)
        self.tariff.mark_immutable()
        self.tariff.make_default()

        self.loop = asyncio.get_event_loop()

    def tearDown(self):
        self.loop.close()

    def _get_report(self, client, customer_id, start_time, end_time, report_format, filename=None, report_is_ready=False):
        if not report_is_ready:
            report = client.customer.report(customer_id, start_time, end_time, report_format=report_format)
            self.assertEqual(report.json["status"], "started")

        report = client.customer.report(customer_id, start_time, end_time, report_format=report_format)
        if report_format == "json":
            self.assertEqual(report.content_type, "application/json")
            report = report.json
            self.assertEqual(report["status"], "completed")
            return report["report"]
        if report_format == "csv":
            self.assertEqual(report.content_type, "text/csv")

        tempdir = tempfile.gettempdir() or ""
        filename = filename or report.content_disposition.split("''", 1)[1]
        try:
            with open(os.path.join(tempdir, filename), "wb") as f:
                f.write(report.body)
        except IOError as e:
            print("Can't save file", filename, e)

        return report.body

    def get_report(self, customer_id, start_time, end_time, report_format, filename=None, report_is_ready=False):
        return self._get_report(self.admin_client, customer_id, start_time, end_time,
                                report_format, filename, report_is_ready)

    def get_report_me(self, start_time, end_time, report_format, filename=None, report_is_ready=False):
        return self._get_report(self.cabinet_client, "me", start_time, end_time,
                                report_format, filename, report_is_ready)

    def test_collector(self):
        start_time = datetime.datetime(2015, 3, 20, 9, 12)
        end_time = datetime.datetime(2015, 5, 1)
        project = Tenant("boss", start_time)

        disk = Disk(project, "test_disk", start_time, 1234567890)
        disk2 = Disk(project, "test_disk2", start_time, 3456)
        volume = Volume(project, "figvam", datetime.datetime.now(), 2)
        vm = Instance(project, "teamcity", "Nano")
        vm2 = Instance(project, "teamcity1", "TestFlavor")

        disk.repeat_message(start_time, end_time)
        disk2.repeat_message(start_time, end_time)
        vm.repeat_message(start_time, end_time)
        vm2.repeat_message(start_time, end_time)
        volume.repeat_message(start_time, end_time)

        hour_price = Decimal(self.volume_size_price) * 2 + Decimal(self.image_size_price) * 3 + \
             + Decimal(self.nano_price)

        with mock.patch("os_interfaces.openstack_wrapper.openstack") as openstack:
            openstack.get_tenant_usage = project.usage
            project.prepare_messages()

            tenants_usage = self.collector.run_usage_collection(end_time + datetime.timedelta(hours=10))
            tenant_usage = next(iter(tenants_usage.values()))
            self.assertTrue(tenant_usage)
            self.assertEqual(self.collector.errors, 0)
            for time_label, time_label_usage in tenant_usage.items():
                withdraw = time_label_usage[1]
                self.assertLess(withdraw - hour_price, 1e-6)
                for usage in time_label_usage[0]:
                    if usage["service_id"] == "image.size":
                        self.assertEqual(usage.volume, 1234567890)
                    if usage['service_id'] == "volume.size":
                        self.assertEqual(usage.volume, 2 * 1073741824) # 2GB

        self.assertEqual(outbox[1].subject, '%s: Notice on service adding notification' % conf.provider.cloud_name)

        account = Customer.get_by_id(project.customer_id).account_dict()["RUB"]
        self.assertEqual(account["balance"], Decimal(project.start_balance))
        hours = int((end_time - start_time).total_seconds() // 3600) + 1
        total_cost = hours * hour_price
        self.assertLess(abs(account["withdraw"] - total_cost), 0.0001)

        report = self.get_report(project.customer_id, start_time, end_time, "json")
        self.assertEqual(report["total"]["RUB"], decimal_to_string(total_cost))

        report = self.get_report(project.customer_id, start_time, end_time, "json", report_is_ready=True)

        report_ru = self.get_report(project.customer_id, start_time, end_time, "csv")
        customer = Customer.get_by_id(project.customer_id)
        customer.locale = "en_us"
        db.session.commit()
        report_en = self.get_report(project.customer_id, start_time, end_time, "csv", filename="report_en.csv")
        self.assertNotEqual(report_ru, report_en)
        self.assertGreater(report_ru.count(b";"), 0)
        self.assertEqual(report_en.count(b";"), 0)

        # pdf en
        self.get_report(project.customer_id, start_time, end_time, "pdf")
        customer = Customer.get_by_id(project.customer_id)
        customer.locale = "ru_ru"
        db.session.commit()

        # pdf ru
        self.get_report(project.customer_id, start_time, end_time, "pdf")
        # json after pdf
        json_report = self.get_report(project.customer_id, start_time, end_time, "json", report_is_ready=True)

        self.cabinet_client.auth(project.customer_email, project.customer_password)
        customer_report = self.get_report_me(start_time, end_time, "json", report_is_ready=True)
        self.assertEqual(json_report, customer_report)

        self.get_report_me(start_time - datetime.timedelta(days=30), start_time, "csv", filename="empty.csv")
        self.get_report_me(start_time - datetime.timedelta(days=30), start_time, "pdf", filename="empty.pdf")

    def test_collector_sequence(self):
        start_time = datetime.datetime(2015, 3, 20, 9, 12)
        end_time = datetime.datetime(2015, 3, 21)

        project = Tenant("boss", start_time)

        disk = Disk(project, "test_disk", start_time, 1234567890)
        hour_price = Decimal(self.image_size_price)*2

        t = start_time
        count = 0
        while t < end_time:
            disk.repeat_message(t, t + datetime.timedelta(hours=1))

            with mock.patch("os_interfaces.openstack_wrapper.openstack") as openstack:
                openstack.get_tenant_usage = project.usage
                project.prepare_messages()

                tenants_usage = self.collector.run_usage_collection(t + datetime.timedelta(hours=1, minutes=10))
                self.assertTrue(tenants_usage[project.project_id])
            t += datetime.timedelta(hours=1)
            count += 1

        account = Customer.get_by_id(project.customer_id).account_dict()["RUB"]
        hours = int((end_time - start_time).total_seconds() // 3600) + 1
        total_cost = hours * hour_price
        self.assertLess(abs(account["withdraw"] - total_cost), 0.0001)

    def _test_collector(self):
        # full test of collector daemon
        @asyncio.coroutine
        def test():
            yield from asyncio.sleep(1)
            self.collector.stop()

        self.loop.run_until_complete(asyncio.wait([self.collector.start(), test()]))
