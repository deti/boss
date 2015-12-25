from api_tests.admin_backend import AdminBackendTestCase
import entities
from utils.context_managers import TemporaryLogout


class SimpleServiceTests(AdminBackendTestCase):
    def test_list_categories(self):
        category_list = self.default_admin_client.service.list_categories()
        self.assertGreater(len(category_list), 0)
        self.assertIsInstance(category_list, list)
        for category in category_list:
            self.assertIn('category_id', category)
            with self.subTest(category_id=category['category_id']):
                self.assertIn('localized_name', category)
                localized_name = category['localized_name']
                self.assertGreater(len(localized_name), 0)

        with self.assertRaisesHTTPError(401), TemporaryLogout(self.default_admin_client):
            self.default_admin_client.service.list_categories()

    def test_get_service(self):
        service_list = self.default_admin_client.service.list()['items'][:3]
        for service in service_list:
            recvd_service = self.default_admin_client.service.get(service['service_id'])
            self.assertDictEqual(recvd_service, service)

    def test_get_unknown_service(self):
        with self.assertRaisesHTTPError(404):
            self.default_admin_client.service.get(12956129859)

    def test_list_service(self):
        service_list = self.default_admin_client.service.list()
        self.assertGreater(len(service_list['items']), 0)

        category_list = self.default_admin_client.service.list_categories()
        category_ids = [cat['category_id'] for cat in category_list]
        category_ids = ','.join(category_ids)

        list_by_all_categories = self.default_admin_client.service.list(category=category_ids)['items']
        full_list = self.default_admin_client.service.list()['items']
        self.assertCountEqual(full_list, list_by_all_categories)

    def test_list_measure(self):
        measure_list = self.default_admin_client.service.list_measure()
        self.assertGreater(len(measure_list), 0)

    def test_remove_used_service(self):
        service = self.create_service(immutable=True)
        self.create_tariff([(service['service_id'], 123)], immutable=True)
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.service.delete(service['service_id'])


class TestCustomServiceUpdate(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.service = self.create_service()

    def test_service_update(self):
        new_localized_name = {'en': entities.Service(self).basic_name('some')}

        service = self.default_admin_client.service.update(self.service['service_id'], localized_name=new_localized_name)
        self.assertEqual(service['localized_name']['en'], new_localized_name['en'])

        new_description = {'en': entities.Service(self).basic_name('some')}

        service = self.default_admin_client.service.update(self.service['service_id'], description=new_description)
        self.assertEqual(service['description']['en'], new_description['en'])

        new_measure_id = 'byte'

        with self.assertRaisesHTTPError(400):
            self.default_admin_client.service.update(self.service['service_id'], measure=new_measure_id)


class TestCustomServiceImmutable(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.service = self.create_service()

    def test_custom_service_immutable(self):
        service_info = self.default_admin_client.service.get(self.service['service_id'])
        self.assertTrue(service_info['mutable'])
        self.default_admin_client.service.immutable(self.service['service_id'])
        service_info = self.default_admin_client.service.get(self.service['service_id'])
        self.assertFalse(service_info['mutable'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.service.update(self.service['service_id'], measure=self.service['measure']['measure_id'])


class TestDeletedCustomServiceOperations(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.service = self.create_service()
        self.default_admin_client.service.delete(self.service['service_id'])

    def test_updating_deleted_custom_service(self):
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.service.update(self.service['service_id'], description=self.service['description'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.service.delete(self.service['service_id'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.service.immutable(self.service['service_id'])


class TestFlavorService(AdminBackendTestCase):
    default_vcpus = 1
    default_ram = 200
    default_disk = 200
    default_network = 1

    def create_flavor_service(self):
        localized_name = entities.Entity(self).localized_name()
        self.addCleanupDelete('service')
        return self.default_admin_client.service.create_vm('flavor_service', localized_name=localized_name,
                                                           vcpus=self.default_vcpus, ram=self.default_ram,
                                                           disk=self.default_disk, network=self.default_network)

    def test_flavor_service(self):
        service_info = self.create_flavor_service()

        service_list = self.default_admin_client.service.list(category='vm')['items']
        self.assertInList(service_list, lambda service: service['localized_name']['en'] == service_info['localized_name']['en'])

        new_vcpus = self.default_vcpus + 1
        new_service_info = self.default_admin_client.service.update_vm(service_info['service_id'], vcpus=new_vcpus)
        self.assertEqual(new_service_info['flavor']['vcpus'], new_vcpus)