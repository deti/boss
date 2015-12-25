import conf
import csv
import tempfile
import os
import uuid
import mock
from tests.base import TestCaseApi
from datetime import datetime, timedelta
from model import db, Customer, Tenant
from arrow import utcnow
from decimal import Decimal
from unittest import TestCase
from report.segments import WeightSegments
from os_interfaces.openstack_wrapper import openstack
from mock import patch


class TestReportApi(TestCaseApi):

    def store_report_to_file(self, report, filename=None):
        tempdir = tempfile.gettempdir() or ""
        tempdir = os.path.join(tempdir, "boss_test_report")
        try:
            os.mkdir(tempdir)
        except OSError:
            pass
        filename = filename or report.content_disposition.split("''", 1)[1]
        try:
            with open(os.path.join(tempdir, filename), "wb") as f:
                f.write(report.body)
        except IOError as e:
            print("Can't save file", filename, e)

    def extract_report(self, method, params, filename=None, report_is_ready=False):
        if not report_is_ready:
            report = method(**params)
            self.assertEqual(report.json["status"], "started")

        formats = {
            "application/json": "json",
            "application/pdf": "pdf",
            "text/csv": "csv"
        }

        report = method(**params)
        report_format = params.get("report_format")
        if report_format is None:
            report_format = formats[report.content_type]

        if report_format == "json":
            self.assertEqual(report.content_type, "application/json")
            report = report.json
            self.assertEqual(report["status"], "completed")
            return report["report"]
        if report_format == "csv":
            self.assertEqual(report.content_type, "text/csv")

        self.store_report_to_file(report, filename)

        return report.body

    def get_customer_report(self, customer_id, start, finish, report_format, report_type="simple",
                            filename=None, report_is_ready=False):
        params = {"customer_id": customer_id,
                  "start": start,
                  "finish": finish,
                  "report_type": report_type,
                  "report_format": report_format}
        return self.extract_report(self.admin_client.customer.report, params, filename, report_is_ready)

    def get_customer_report_me(self, client, start, finish, report_format,
                            filename=None, report_is_ready=False):
        params = {"customer_id": "me",
                  "start": start,
                  "end": finish,
                  "report_format": report_format}
        return self.extract_report(self.cabinet_client.customer.report, params, filename, report_is_ready)

    def get_report(self, report_type, start, finish, report_format, filename=None,
                   report_is_ready=False, locale=None):
        params = {"start": start,
                  "finish": finish,
                  "report_format": report_format,
                  "locale": locale
                  }
        report_method = getattr(self.admin_client.report, report_type)
        return self.extract_report(report_method, params, filename, report_is_ready)

    def test_receipts_report(self):
        self.create_tariff("default_tariff", default=True)
        customer_info = self.create_customer_by_self("recipts_report@example.com")
        db.session.commit()
        customer_id = customer_info["customer_id"]
        self.admin_client.customer.update_balance(customer_id, "100", "test withdraw for test mode", "RUB")

        self.admin_client.customer.update(customer_id, detailed_info={"passport_series_number": "1234 567 890",
                                                                      "passport_issued_by": "UFMS Russia",
                                                                      "passport_issued_date": "2013-01-01"})
        customer_db = Customer.get_by_id(customer_id)
        customer_db.confirm_email()

        self.admin_client.customer.make_prod(customer_id)
        self.admin_client.customer.update_balance(customer_id, "100", "test withdraw for prod mode", "RUB")

        start = utcnow().datetime - timedelta(days=30)
        end = utcnow().datetime + timedelta(hours=1)

        report = self.get_report("receipts", start, end, "csv")
        self.assertTrue(report)
        self.assertGreater(report.count(b";"), 5)
        report = [row for row in report.split(b"\r\n") if row]
        self.assertEqual(len(report), 2)  # header + balance update after prod

        self.get_report("receipts", start, end, "tsv")

    def test_usage_report(self):
        self.create_tariff("default_tariff", default=True)
        customer_info = self.create_customer_by_self("test_usage1@example.com")

        customer = Customer.get_by_id(customer_info["customer_id"])
        tenant = Tenant.create(uuid.uuid4().hex, "test tenant")

        customer.os_tenant_id = tenant.tenant_id
        db.session.commit()

        start = datetime(2015, 4, 1)
        end = datetime(2015, 4, 25)
        end_report = end + timedelta(hours=24)
        cost1 = Decimal(0)
        cost1 += Customer.fake_usage(customer, start, end, self.service_nano_id, uuid.uuid4().hex, 1)
        cost1 += Customer.fake_usage(customer, start + timedelta(days=5), end, self.service_micro_id, uuid.uuid4().hex, 1)
        cost1 += Customer.fake_usage(customer, start + timedelta(days=6), end, self.service_nano_id, uuid.uuid4().hex, 1)
        cost1 += Customer.fake_usage(customer, start, end, "storage.image", uuid.uuid4().hex, 60*conf.GIGA)

        customer2_info = self.create_customer("test_usage2@example.com")
        tenant2 = Tenant.create(uuid.uuid4().hex, "test tenant 2")
        customer2 = Customer.get_by_id(customer2_info["customer_id"])
        customer2.os_tenant_id = tenant2.tenant_id
        cost2 = Customer.fake_usage(customer2, start, end, self.service_nano_id, uuid.uuid4().hex, 1)
        db.session.commit()

        report = self.get_report("usage", start, end_report, "csv", locale="en_us")
        self.assertTrue(report)

        report = [row.decode("ascii") for row in report.split(b"\r\n") if row]

        parsed_report = csv.reader(report)
        cust_1 = [row for row in parsed_report if row[0] == 'test_usage1@example.com']
        cust_1_cost = sum(Decimal(row[1]) for row in cust_1)
        parsed_report = csv.reader(report)
        cust_2 = [row for row in parsed_report if row[0] == 'test_usage2@example.com']
        cust_2_cost = sum(Decimal(row[1]) for row in cust_2)
        self.assertEqual(len(cust_2), 1)
        self.assertEqual(len(cust_1), 1)
        self.assertEqual(cust_1_cost, cost1)
        self.assertEqual(cust_2_cost, cost2)

    def service_cost(self, price, start, end, volume=1):
        start = start.replace(minute=0, second=0, microsecond=0)
        end = end.replace(minute=59, second=59, microsecond=999999)
        hours = int((end - start + timedelta(seconds=1)).total_seconds()) // 3600
        return hours * Decimal(price) * volume

    def test_report_with_two_tariffs(self):
        prepay_entity_customer = {"customer_type": "entity", "detailed_info": {
            "name": "test prepay entity customer", "contract_number": "2015/4568",
            "contract_date": "2015-01-01", "organization_type": "OOO", "name": "Some Company",
            "full_organization_name": "OOO Some Company", "primary_state_registration_number": "159 8525 15552",
            "individual_tax_number": "52 59 5555555", "legal_address_country": "RU", "legal_address_city": "NN",
            "legal_address_address": "Ошарская, 13", "location_country": "RU", "location_city": "NN",
            "location_address": "Ошарская", "general_manager_name": "Васильев Е.В",
            "general_accountant_name": "Иванова В.Н", "contact_person_name": "Петров Василий"
        }}
        self.create_tariff("First Tariff", default=True)
        customer_info = self.create_customer("test_invoice@example.com", **prepay_entity_customer)
        customer_id = customer_info["customer_id"]

        customer = Customer.get_by_id(customer_id)
        tenant = Tenant.create(uuid.uuid4().hex, "test tenant")
        tenant_id = tenant.tenant_id

        customer.os_tenant_id = tenant_id
        db.session.commit()

        start = datetime(2015, 4, 1)
        middle_end = datetime(2015, 4, 1, 15) - timedelta(seconds=1)
        end = datetime(2015, 4, 2) - timedelta(seconds=1)
        end_second = datetime(2015, 4, 3) - timedelta(seconds=1)
        end_report = end_second + timedelta(hours=24)
        vm_nano = uuid.uuid4().hex
        vm_small = uuid.uuid4().hex
        vm_nano2 = "nano2"

        storage_id = "disk1"

        Customer.fake_usage(customer, start, end, self.service_nano_id, vm_nano, 1, resource_name="nano1")
        Customer.fake_usage(customer, start, end, self.service_small_id, vm_small, 1, resource_name="my little pony")
        Customer.fake_usage(customer, start, middle_end , self.service_nano_id, vm_nano2, 1, resource_name="pico")
        Customer.fake_usage(customer, start, middle_end, "storage.volume", storage_id, 1237852421)
        Customer.fake_usage(customer, middle_end + timedelta(hours=1), end, "storage.volume", storage_id, 77777777777)
        Customer.fake_usage(customer, start, end, "net.allocated_ip", "ip_floating_1", 3, resource_name="192.168.1.1")
        Customer.fake_usage(customer, start, end, "net.allocated_ip", "ip_floating_2", 7)
        db.session.commit()

        second_tariff = self.create_tariff("Second Tariff", default=True)
        self.admin_client.customer.update(customer_id, tariff=second_tariff["tariff_id"])

        customer = Customer.get_by_id(customer_id)
        customer.confirm_email()  # clear db session

        customer = Customer.get_by_id(customer_id)
        customer.os_tenant_id = tenant_id  # confirm email cleared tenant id
        Customer.fake_usage(customer, end + timedelta(minutes=1), end_second, self.service_nano_id, vm_nano, 1,
                            resource_name="nano1")
        db.session.commit()

        report_tsv = self.get_customer_report(customer_id, start, end_report, "tsv", "detailed")
        report_csv = self.get_customer_report(customer_id, start, end_report, "csv", "detailed")

        report = self.get_customer_report(customer_id, start, end_report, "pdf", "detailed", filename="detailed.pdf")

        report_json = self.get_customer_report(customer_id, start, end_report, "json", "detailed")

        nano_cost = self.service_cost("2.23", start, end)
        nano2_cost = self.service_cost("2.23", start, middle_end)
        small_cost = self.service_cost("12.23", start, end)
        ip_floating_1_cost = self.service_cost("43.45", start, end)*3
        ip_floating_2_cost = self.service_cost("43.45", start, end)*7

        t1_cost = nano_cost + small_cost + nano2_cost + ip_floating_1_cost + ip_floating_2_cost
        self.assertEqual(len(report_json["tariffs"]), 2)
        self.assertEqual(Decimal(report_json["tariffs"][0]["total_cost"]), t1_cost)

        t2_cost = self.service_cost("2.23", end + timedelta(minutes=1), end_second)
        self.assertEqual(Decimal(report_json["tariffs"][1]["total_cost"]), t2_cost)

        self.assertEqual(Decimal(report_json["total"]["RUB"]), t1_cost + t2_cost)


        report = self.get_customer_report(customer_id, start, end_report, "pdf", filename="two_tariff.pdf")
        self.assertTrue(report)

        report = self.get_customer_report(customer_id, start, end_report, "csv", filename="two_tariff.csv")
        self.assertTrue(report)

        report = self.get_customer_report(customer_id, start, end_report, "tsv", filename="two_tariff.tsv")
        self.assertTrue(report)

        report_simple_json = self.get_customer_report(customer_id, start, end_report, "json", filename="two_tariff.pdf")
        self.assertTrue(report_simple_json)

        self.assertEqual(Decimal(report_simple_json["total"]["RUB"]), t1_cost + t2_cost)

        report = self.get_customer_report(customer_id, start, end_report, "pdf", "acceptance_act")

        report = self.get_customer_report(customer_id, end_report + timedelta(days=1),
                                          end_second + timedelta(days=31), "pdf", filename="empty.pdf")

    def test_report_unknown_service(self):
        prepay_entity_customer = {"customer_type": "entity", "detailed_info": {
            "name": "test prepay entity customer", "contract_number": "2015/4568",
            "contract_date": "2015-01-01", "organization_type": "OOO", "name": "Some Company",
            "full_organization_name": "OOO Some Company", "primary_state_registration_number": "159 8525 15552",
            "individual_tax_number": "52 59 5555555", "legal_address_country": "RU", "legal_address_city": "NN",
            "legal_address_address": "Ошарская, 13", "location_country": "RU", "location_city": "NN",
            "location_address": "Ошарская", "general_manager_name": "Васильев Е.В",
            "general_accountant_name": "Иванова В.Н", "contact_person_name": "Петров Василий"
        }}
        self.create_tariff("First Tariff", default=True)
        customer_info = self.create_customer("test_invoice@example.com", **prepay_entity_customer)
        customer_id = customer_info["customer_id"]

        customer = Customer.get_by_id(customer_id)
        tenant = Tenant.create(uuid.uuid4().hex, "test tenant")
        tenant_id = tenant.tenant_id
        customer.confirm_email()  # clear db session
        customer.os_tenant_id = tenant_id
        db.session.commit()

        start = datetime(2015, 4, 1)
        end = datetime(2015, 4, 1, 10) - timedelta(seconds=1)
        customer = Customer.get_by_id(customer_id)
        Customer.fake_usage(customer, start, end, "service_unknown", "unknown resource", 1)
        db.session.commit()

        report = self.get_customer_report(customer_id, start, end, "pdf", filename="unknown_service.pdf")
        self.assertTrue(report)

        report = self.get_customer_report(customer_id, start, end, "pdf", filename="unknown_service_detailed.pdf",
                                          report_type="detailed")
        self.assertTrue(report)

    def test_invoice(self):
        prepay_entity_customer = {"customer_type": "entity", "detailed_info": {
            "name": "test prepay entity customer", "contract_number": "2015/4568",
            "contract_date": "2015-01-01", "organization_type": "OOO", "name": "Some Company",
            "full_organization_name": "OOO Some Company", "primary_state_registration_number": "159 8525 15552",
            "individual_tax_number": "52 59 5555555", "legal_address_country": "RU", "legal_address_city": "NN",
            "legal_address_address": "Ошарская, 13", "location_country": "RU", "location_city": "NN",
            "location_address": "Ошарская", "general_manager_name": "Васильев Е.В",
            "general_accountant_name": "Иванова В.Н", "contact_person_name": "Петров Василий"
        }}
        self.create_tariff("First Tariff", default=True)
        customer_info = self.create_customer("test_invoice@example.com", **prepay_entity_customer)
        rendered_pdf = self.admin_client.customer.invoice(customer_info["customer_id"], "9200.0")

        self.store_report_to_file(rendered_pdf)

        self.cabinet_client.auth(customer_info["email"], customer_info["password"])
        rendered_pdf = self.cabinet_client.customer.invoice("me", "9200.0")
        self.store_report_to_file(rendered_pdf, filename="customer_invoice.pdf")

    def test_customers_stats(self):
        self.create_tariff("stat")
        self.create_customer("one@mail.ru")
        blocked = self.create_customer("blocked@mail.ru")
        self.admin_client.customer.block(blocked["customer_id"])
        entity = self.create_customer("legal@mail.ru")
        self.admin_client.customer.update(entity["customer_id"], customer_type="entity")
        self.create_customer("prod@mail.ru", make_prod=True)
        deleted = self.create_customer("deleted@mail.ru", make_prod=True)
        self.admin_client.customer.delete(deleted["customer_id"])
        stat = self.admin_client.stats.customers_stats()
        self.assertEqual(stat["test_entity"], 1)
        self.assertEqual(stat["total_deleted"], 1)
        self.assertEqual(stat["test_private_blocked"], 1)
        self.assertEqual(stat["test_private"], 2)
        self.assertEqual(stat["private_deleted"], 1)
        self.assertEqual(stat["total_production"], 2)
        self.assertEqual(stat["production_private"], 2)
        self.assertEqual(stat["total_test"], 3)
        self.assertEqual(stat["total"], 5)
        self.assertEqual(stat["total_blocked"], 1)

    @mock.patch.object(openstack, 'get_floating_ips', return_value=None)
    def test_stats_ipaddress(self, get_floating_ips):
        self.create_tariff("stat")
        self.create_customer("one@mail.ru")

        blocked = self.create_customer("blocked@mail.ru")
        self.admin_client.customer.block(blocked["customer_id"])

        entity = self.create_customer("legal@mail.ru")
        self.admin_client.customer.update(entity["customer_id"], customer_type="entity")
        self.create_customer("prod@mail.ru", make_prod=True)

        deleted = self.create_customer("deleted@mail.ru", make_prod=True)
        self.admin_client.customer.delete(deleted["customer_id"])

        ips_result = [
            [{'fixed_ip_address': None,
              'floating_ip_address': '192.168.122.222',
              'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
              'id': '2e767009-9626-4849-b3b4-83c8b9e4d1ec',
              'port_id': None,
              'router_id': None,
              'status': 'DOWN',
              'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'},
             {'fixed_ip_address': None,
              'floating_ip_address': '192.168.122.220',
              'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
              'id': '9a31e9ff-6b23-43e6-afad-ddd3ba194597',
              'port_id': None,
              'router_id': None,
              'status': 'DOWN',
              'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'}],
            [{'fixed_ip_address': None,
              'floating_ip_address': '192.168.122.250',
              'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
              'id': 'be5b5861-358e-4ba8-afec-a22af29de776',
              'port_id': None,
              'router_id': None,
              'status': 'UP',
              'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'}],
            [{'fixed_ip_address': None,
              'floating_ip_address': '192.168.122.250',
              'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
              'id': 'be5b5861-358e-4ba8-afec-a22af29de776',
              'port_id': None,
              'router_id': None,
              'status': 'UP',
              'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'}],
            [{'fixed_ip_address': None,
              'floating_ip_address': '192.168.122.250',
              'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
              'id': 'be5b5861-358e-4ba8-afec-a22af29de776',
              'port_id': None,
              'router_id': None,
              'status': 'DOWN',
              'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'}],
        ]
        get_floating_ips.side_effect = ips_result
        res = self.admin_client.stats.stat_ips()
        expected_result = {
            'active_customer': 4,
            'blocked_customer': 1,
            'customer_mode-production': 1,
            'customer_mode-test': 4,
            'customer_type-entity': 1,
            'customer_type-private': 4,
            'ip_status-DOWN': 3,
            'ip_status-UP': 2,
            'total': 5}
        self.assertEqual(res['floating_ips'], expected_result)

    @patch("os_interfaces.openstack_wrapper.openstack.get_tenants", return_value=[])
    def test_openstack_usage(self, get_tenants):
        from statistics import OpenstackUsage

        OpenstackUsage().stat()
        report = self.extract_report(self.admin_client.stats.openstack_usage, {})
        self.assertTrue(report)


class TestWeightSegment(TestCase):
    def test_segments(self):
        s = WeightSegments(1)

        s.add_range(50, 60)
        self.assertEqual(s.edges, [50, 60])

        self.assertTrue(str(s))

        s.add_range(50, 60)
        self.assertEqual(s.edges, [50, 60])

        s.add_range(70, 80)
        self.assertEqual(s.edges, [50, 60, 70, 80])

        s.add_range(30, 40)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 40)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 41)
        self.assertEqual(s.edges, [30, 41, 50, 60, 70, 80])
        self.assertEqual(list(s.in_range(35, 55)), [((35, 41), 1), ((50, 55), 1)])
        self.assertEqual(list(s.in_range(0, 10)), [])

        self.assertEqual(s.length(), 12+11+11)
        self.assertEqual(s.in_range(35, 55).length(), 7+6)
        self.assertEqual(s.in_range(35, 65).length(), 7+11)
        self.assertEqual(s.in_range(35, 75).length(), 7+11+6)
        self.assertEqual(s.in_range(0, 1000).length(), 12+11+11)
        serialized = s.serialize_str()
        s2 = WeightSegments.deserialize_str(serialized, s.deviation)
        self.assertEqual(s, s2)

        ss = WeightSegments.deserialize_str("garbage", s.deviation)
        self.assertEqual(ss, WeightSegments(s.deviation))

        s.add_range(30, 51)
        self.assertEqual(s.edges, [30, 60, 70, 80])

        s.add_range(35, 71)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(35, 71)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(29, 81)
        self.assertEqual(s.edges, [29, 81])

        s.add_range(100, 110)
        self.assertEqual(s.edges, [29, 81, 100, 110])

        s.add_range(90, 95)
        self.assertEqual(s.edges, [29, 81, 90, 95, 100, 110])

        # the same test, but deviation == 5
        s = WeightSegments(5)

        s.add_range(50, 60)
        self.assertEqual(s.edges, [50, 60])

        s.add_range(50, 60)
        self.assertEqual(s.edges, [50, 60])

        s.add_range(70, 80)
        self.assertEqual(s.edges, [50, 60, 70, 80])

        s.add_range(30, 40)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 40)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 41)
        self.assertEqual(s.edges, [30, 41, 50, 60, 70, 80])

        s.add_range(30, 51)
        self.assertEqual(s.edges, [30, 60, 70, 80])

        s.add_range(35, 71)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(35, 71)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(29, 81)
        self.assertEqual(s.edges, [29, 81])

        s.add_range(100, 110)
        self.assertEqual(s.edges, [29, 81, 100, 110])

        s.add_range(90, 95)
        self.assertEqual(s.edges, [29, 81, 90, 110])

        s.add_range(85, 95)
        self.assertEqual(s.edges, [29, 110])

        s.add_range(115, 116)
        self.assertEqual(s.edges, [29, 116])

        s.add_range(23, 24)
        self.assertEqual(s.edges, [23, 116])

        s.add_range(16, 17)
        self.assertEqual(s.edges, [16, 17, 23, 116])

    def test_weight_segments(self):
        s = WeightSegments(1)

        self.assertEqual(len(s), 0)
        self.assertFalse(s)

        s.add_range(50, 60, 3)
        self.assertEqual(s.edges, [50, 60])
        self.assertEqual(s.weights, [3])
        self.assertEqual(len(s), 1)
        self.assertTrue(s)

        s.add_range(50, 60, 5)
        self.assertEqual(s.edges, [50, 60])
        self.assertEqual(s.weights, [5])

        s.add_range(70, 80, 7)
        self.assertEqual(s.edges, [50, 60, 70, 80])
        self.assertEqual(s.weights, [5, 7])

        s.add_range(30, 40, 11)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])
        self.assertEqual(s.weights, [11, 5, 7])

        s.add_range(30, 40, 13)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])
        self.assertEqual(s.weights, [13, 5, 7])

        s.add_range(30, 41, 17)
        self.assertEqual(s.edges, [30, 41, 50, 60, 70, 80])
        self.assertEqual(s.weights, [17, 5, 7])

        s.add_range(30, 41, 17)
        self.assertEqual(s.edges, [30, 41, 50, 60, 70, 80])
        self.assertEqual(s.weights, [17, 5, 7])

        self.assertEqual(list(s.in_range(35, 55)), [((35, 41), 17), ((50, 55), 5)])
        self.assertEqual(list(s.in_range(0, 10)), [])

        self.assertEqual(s.weight(), 12*17 + 11*5 + 11*7)
        self.assertEqual(s.in_range(35, 55).weight(), 7*17+6*5)
        self.assertEqual(s.in_range(35, 65).weight(), 7*17+11*5)
        self.assertEqual(s.in_range(35, 75).weight(), 7*17+11*5+6*7)
        self.assertEqual(s.in_range(0, 1000).weight(), 12*17+11*5+11*7)

        s.add_range(30, 51, 19)
        self.assertEqual(s.edges, [30, 51, 52, 60, 70, 80])
        self.assertEqual(s.weights, [19, 5, 7])

        s.add_range(35, 71, 23)
        self.assertEqual(s.edges, [30, 34, 35, 71, 72, 80])
        self.assertEqual(s.weights, [19, 23, 7])

        s.add_range(35, 71, 29)
        self.assertEqual(s.edges, [30, 34, 35, 71, 72, 80])
        self.assertEqual(s.weights, [19, 29, 7])

        s.add_range(29, 81, 31)
        self.assertEqual(s.edges, [29, 81])
        self.assertEqual(s.weights, [31])

        s.add_range(100, 110, 37)
        self.assertEqual(s.edges, [29, 81, 100, 110])
        self.assertEqual(s.weights, [31, 37])

        s.add_range(90, 95, 41)
        self.assertEqual(s.edges, [29, 81, 90, 95, 100, 110])
        self.assertEqual(s.weights, [31, 41, 37])

        s.add_range(82, 85, 31)
        self.assertEqual(s.edges, [29, 85, 90, 95, 100, 110])
        self.assertEqual(s.weights, [31, 41, 37])

        s.add_range(86, 89, 31)
        self.assertEqual(s.edges, [29, 89, 90, 95, 100, 110])
        self.assertEqual(s.weights, [31, 41, 37])

        s.add_range(99, 106, 31)
        self.assertEqual(s.edges, [29, 89, 90, 95, 99, 106, 107, 110])
        self.assertEqual(s.weights, [31, 41, 31, 37])

        s.add_range(90, 98, 31)
        self.assertEqual(s.edges, [29, 106, 107, 110])
        self.assertEqual(s.weights, [31, 37])

        s.add_range(108, 110, 31)
        self.assertEqual(s.edges, [29, 106, 107, 107, 108, 110])
        self.assertEqual(s.weights, [31, 37, 31])

        s.add_range(111, 200, 31)
        self.assertEqual(s.edges, [29, 106, 107, 107, 108, 200])
        self.assertEqual(s.weights, [31, 37, 31])

        s.add_range(201, 210, 31)
        self.assertEqual(s.edges, [29, 106, 107, 107, 108, 210])
        self.assertEqual(s.weights, [31, 37, 31])

        s.add_range(107, 107, 31)
        self.assertEqual(s.edges, [29, 210])
        self.assertEqual(s.weights, [31])

        s.add_range(50, 60, 1)
        self.assertEqual(s.edges, [29, 49, 50, 60, 61, 210])
        self.assertEqual(s.weights, [31, 1, 31])

        s.add_range(50, 60, 31)
        self.assertEqual(s.edges, [29, 210])
        self.assertEqual(s.weights, [31])

        # the same test, but deviation == 5
        s = WeightSegments(5)

        s.add_range(50, 60, 1)
        self.assertEqual(s.edges, [50, 60])
        self.assertEqual(s.weights, [1])

        s.add_range(50, 60, 1)
        self.assertEqual(s.edges, [50, 60])

        s.add_range(70, 80, 1)
        self.assertEqual(s.edges, [50, 60, 70, 80])

        s.add_range(30, 40, 1)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 40, 1)
        self.assertEqual(s.edges, [30, 40, 50, 60, 70, 80])

        s.add_range(30, 41, 1)
        self.assertEqual(s.edges, [30, 41, 50, 60, 70, 80])

        s.add_range(30, 51, 1)
        self.assertEqual(s.edges, [30, 60, 70, 80])

        s.add_range(35, 71, 1)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(35, 71, 1)
        self.assertEqual(s.edges, [30, 80])

        s.add_range(29, 81, 1)
        self.assertEqual(s.edges, [29, 81])

        s.add_range(100, 110, 1)
        self.assertEqual(s.edges, [29, 81, 100, 110])

        s.add_range(90, 95, 1)
        self.assertEqual(s.edges, [29, 81, 90, 110])

        s.add_range(85, 95, 1)
        self.assertEqual(s.edges, [29, 110])

        s.add_range(115, 116, 1)
        self.assertEqual(s.edges, [29, 116])

        s.add_range(23, 24, 1)
        self.assertEqual(s.edges, [23, 116])

        s.add_range(16, 17, 1)
        self.assertEqual(s.edges, [16, 17, 23, 116])
