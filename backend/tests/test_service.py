import errors
import mock
from tests.base import TestCaseApi
from model import Service
from os_interfaces.openstack_wrapper import openstack


class TestServiceApi(TestCaseApi):
    new_flavor_info = {"flavor_id": "TestFlavor", "vcpus": 2, "ram": 512, "disk": 31, "network": 2,
                       "localized_name": '{"ru": "Флавор TestFlavor", "en": "Flavor TestFlavor"}',
                       "description": '{"ru": "Тест Флавор", "en": "Test Flavor"}'}

    def test_service_list(self):
        res = self.admin_client.service.categories()
        self.assertTrue(res)

        length_all = len(self.admin_client.service.list()["service_list"]['items'])
        self.assertTrue(length_all)
        length_net = len(self.admin_client.service.list(category="net")["service_list"]['items'])
        list1 = self.admin_client.service.list(limit=2)["service_list"]['items']
        self.assertTrue(length_net)
        self.assertLess(length_net, length_all)
        self.assertEqual(len(list1), 2)

        list2 = self.admin_client.service.list(limit=2, page=2)["service_list"]['items']

        self.assertNotEqual(list1, list2)

        with self.expect_error(errors.BadRequest):
            self.admin_client.service.list(category="netnetnet")

        m1small = self.admin_client.service.get(self.service_small_id)  # Small
        self.assertEqual(set(m1small.keys()), {"localized_name", "measure", "category", "service_id",
                                               "mutable", "deleted", "description", "flavor", "fixed"})
        self.assertEqual(m1small["service_id"], self.service_small_id)  # Small

        volume = self.admin_client.service.get("storage.volume")
        self.assertEqual(volume["localized_name"],
                         {'en': 'Additional Disks and Snapshots', 'ru': 'Дополнительные Диски и Снапшоты'})
        measure = volume["measure"]
        self.assertEqual(measure["localized_name"], {'en': 'Gb*hour', 'ru': 'Гб*час'})

    def test_service_list_for_custom_category(self):
        self.admin_client.service.create_custom(self.localized_name("Custom Service Name"), "hour",
                                                self.localized_name("Custom service description"))
        all_services = self.admin_client.service.list()["service_list"]['items']
        service_category_ids = [item["category"] for item in all_services]

        custom = {'localized_name': {'ru': 'Дополнительные', 'en': 'Custom'}, 'category_id': 'custom'}

        self.assertIn(custom, service_category_ids)

        first_call_custom_services_count = len(self.admin_client.service.list(category="custom")["service_list"]['items'])
        second_call_custom_services_count = len(self.admin_client.service.list(category="custom")["service_list"]['items'])
        self.assertEqual(first_call_custom_services_count, second_call_custom_services_count)

    def test_custom_service(self):
        lname = self.localized_name("Nginx turning")
        res = self.admin_client.service.create_custom(lname, "hour")
        self.assertTrue(res)
        with self.expect_error(errors.ServiceAlreadyExisted):
            self.admin_client.service.create_custom(lname, "hour")

        unlimited = self.admin_client.service.create_custom(self.localized_name("Unlimited traffic"), "month",
                                                            self.localized_name("Service description"))

        services = self.admin_client.service.list()["service_list"]
        self.assertGreater(len(services), 2)
        custom_services = self.admin_client.service.list(category="custom")["service_list"]['items']

        self.assertEqual(len(custom_services), 2)

        unlimited_modified = self.admin_client.service.update_custom(unlimited["service_id"], measure="hour")

        self.assertEqual(unlimited["measure"]["measure_id"], "month")
        self.assertEqual(unlimited_modified["measure"]["measure_id"], "hour")

        self.admin_client.service.immutable(unlimited["service_id"])

        with self.expect_error(errors.ImmutableService):
            self.admin_client.service.update_custom(unlimited["service_id"], measure="month")

        self.admin_client.service.update_custom(unlimited["service_id"], as_json=True,
                                                description=self.localized_name("updated description"))

        self.admin_client.service.delete(res["service_id"])
        with self.expect_error(errors.RemovedService):
            self.admin_client.service.update_custom(res["service_id"], measure="month")

        with self.expect_error(errors.RemovedService):
            self.admin_client.service.delete(res["service_id"])

        with self.expect_error(errors.RemovedService):
            self.admin_client.service.immutable(res["service_id"])

        tariff = {
            "localized_name": self.localized_name("Тариф"),
            "currency": "USD",
            "description": "",
            "services": [
                {"service_id": self.service_small_id, "price": "12.23"},
                {"service_id": self.service_medium_id, "price": "23.45"}]}

        tariff = self.admin_client.tariff.create(as_json=True, **tariff)

        services = self.extract_services(tariff["services"])
        services.append({"service_id": unlimited["service_id"], "price": "343"})
        tariff = self.admin_client.tariff.update(tariff["tariff_id"], as_json=True, services=services)

        services = self.extract_services(tariff["services"])
        services.append({"service_id": res["service_id"], "price": "343"})
        with self.expect_error(errors.RemovedServiceInTariff):
            self.admin_client.tariff.update(tariff["tariff_id"], as_json=True, services=services)

        services = self.extract_services(tariff["services"])
        mutable_service = self.admin_client.service.create_custom(self.localized_name("Mutable service"), "hour")
        services.append({"service_id": mutable_service["service_id"], "price": "343"})

        with self.expect_error(errors.OnlyImmutableService):
            self.admin_client.tariff.update(tariff["tariff_id"], as_json=True, services=services)

    def test_create_flavor(self):
        service_id = self.admin_client.service.create_vm(**self.new_flavor_info)['service_id']

        with self.expect_error(errors.ServiceAlreadyExisted):
            self.admin_client.service.create_vm(**self.new_flavor_info)

        self.new_flavor_info['localized_name'] = '{"ru": "Флавор Test Flavor", "en": "Flavor Test Flavor"}'

        with self.expect_error(errors.FlavorAlreadyExists):
            self.admin_client.service.create_vm(**self.new_flavor_info)

        self.assertEqual(openstack.create_flavor.call_count, 10)

        service = Service.get_by_id(service_id)

        service.mark_immutable()
        self.assertEqual(openstack.create_flavor.call_count, 11)

        self.new_flavor_info['localized_name'] = '{"ru": "Флавор TestFlavor1", "en": "Flavor TestFlavor1"}'
        self.new_flavor_info['flavor_id'] = "TestFlavor1"
        self.new_flavor_info.pop('network')

        service_id = self.admin_client.service.create_vm(**self.new_flavor_info)['service_id']
        service = Service.get_by_id(service_id)

        self.assertIsNone(service.flavor.network)

        with mock.patch('os_interfaces.openstack_wrapper.openstack.get_nova_flavor',
                        mock.MagicMock(side_effect=self.create_flavor_mock)):
            self.new_flavor_info['localized_name'] = '{"ru": "Флавор TestFlavor2", "en": "Flavor TestFlavor2"}'
            self.new_flavor_info['flavor_id'] = "TestFlavor2"

            with self.expect_error(errors.Conflict):
                service_id = self.admin_client.service.create_vm(**self.new_flavor_info)['service_id']

            self.new_flavor_info['disk'] = 30

            service_id = self.admin_client.service.create_vm(**self.new_flavor_info)['service_id']
            service = Service.get_by_id(service_id)

            self.assertFalse(service.mutable)

    def test_update_flavor(self):
        changed_flavor_info = {"flavor_id": "TestFlavor1", "vcpus": 4, "ram": 1024, "disk": 45, "network": 150}
        service_id = self.admin_client.service.create_vm(**self.new_flavor_info)['service_id']

        updated = self.admin_client.service.update_vm(service_id, **changed_flavor_info)

        self.assertEqual(updated['flavor'], changed_flavor_info)

        with self.expect_error(errors.FlavorAlreadyExists):
            self.admin_client.service.update_vm(service_id, flavor_id='Nano')

        self.admin_client.service.update_vm(service_id, as_json=True, description=self.localized_name('Mega nano'))

        with self.expect_error(errors.ServiceAlreadyExisted):
            self.admin_client.service.update_vm(service_id, localized_name='{"ru": "Виртуальный сервер Small", '
                                                                        '"en": "Virtual server Small"}')

    def test_measure_list(self):
        all_measures = self.admin_client.service.measures()
        time_measures = self.admin_client.service.measures("time")
        self.assertLess(len(time_measures), len(all_measures))
        for m in time_measures:
            self.assertEqual(m["measure_type"], "time")

    def test_force_delete(self):
        self.admin_client.service.create_custom(self.localized_name("$test force delete"), "hour")
        deleted = self.admin_client.delete("/api/0/_force_delete/",
                                           {"tables": "service", "prefix": "$test"}).json["deleted"]
        self.assertEqual(deleted["service"], 1)

