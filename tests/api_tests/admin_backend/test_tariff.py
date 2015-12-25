from api_tests.admin_backend import AdminBackendTestCase
import entities


class SimpleTariffTests(AdminBackendTestCase):
    def test_tariff_list(self):
        tariff_list = self.default_admin_client.tariff.list()
        self.assertEqual(tariff_list['total'], len(tariff_list['items']))

    def test_tariff_update_remove_service(self):
        services = list(self.get_immutable_services())[:2]
        tariff = self.create_tariff(services=[(services[0], 125), (services[1], 125)])
        self.assertEqual(len(tariff['services']), 2)
        tariff = self.default_admin_client.tariff.update(tariff['tariff_id'], services=[{'service_id': services[0], 'price': 124}])
        self.assertEqual(len(tariff['services']), 1)
        self.assertEqual(tariff['services'][0]['service']['service_id'], services[0])

    def test_tariff_mutable_default(self):
        tariff = self.create_tariff()
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.set_default(tariff['tariff_id'])


class DefaultTariffTests(AdminBackendTestCase):
    def setUp(self):
        super().setUp()
        self.tariff1 = self.create_tariff(immutable=True)
        self.tariff2 = self.create_tariff(immutable=True)
        existed_default_tariff = self.check_default_tariff()
        if existed_default_tariff:
            self.addCleanupBeforeDelete(self.default_admin_client.tariff.set_default, existed_default_tariff['tariff_id'])

    def test_default_tariff_setting(self):
        self.assertFalse(self.tariff1['default'])
        self.assertFalse(self.tariff2['default'])

        self.default_admin_client.tariff.set_default(self.tariff1['tariff_id'])
        self.tariff1 = self.default_admin_client.tariff.get(self.tariff1['tariff_id'])
        self.assertTrue(self.tariff1['default'])
        tariff = self.default_admin_client.tariff.get_default()
        self.assertEqual(tariff['tariff_id'], self.tariff1['tariff_id'])

        self.default_admin_client.tariff.set_default(self.tariff2['tariff_id'])
        self.tariff2 = self.default_admin_client.tariff.get(self.tariff2['tariff_id'])
        self.tariff1 = self.default_admin_client.tariff.get(self.tariff1['tariff_id'])
        self.assertTrue(self.tariff2['default'])
        self.assertFalse(self.tariff1['default'])
        tariff = self.default_admin_client.tariff.get_default()
        self.assertEqual(tariff['tariff_id'], self.tariff2['tariff_id'])

    def test_default_tariff_make_default(self):
        self.tariff1 = self.default_admin_client.tariff.set_default(self.tariff1['tariff_id'])
        self.assertTrue(self.tariff1['default'])
        self.tariff1 = self.default_admin_client.tariff.set_default(self.tariff1['tariff_id'])
        self.assertTrue(self.tariff1['default'])

    def test_default_tariff_deleted(self):
        self.default_admin_client.tariff.delete(self.tariff1['tariff_id'])
        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.set_default(self.tariff1['tariff_id'])


class OneTariffTests(AdminBackendTestCase):
    def search_tariff_in_list(self, tariff, tariff_list):
        for tariff in tariff_list['items']:
            if tariff['tariff_id'] == tariff['tariff_id']:
                break
        else:
            self.fail('Tariff {} not found in tariff list'.format(tariff['tariff_id']))

    def search_event_in_history(self, history:list, event:str) -> list:
        resp = [h for h in history if h['event'] == event]
        if len(resp) == 0:
            self.fail('Event {} not found in history list.'.format(event))
        return resp


class TariffOperationsTests(OneTariffTests):
    def setUp(self):
        super().setUp()
        self.tariff = self.create_tariff()

    def test_tariff_conflict_creation(self):
        self.addCleanupDelete('tariff')
        tariff_info = entities.Tariff(self).generate(localized_name=self.tariff['localized_name'])

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.create(**tariff_info)

    def test_tariff_in_list(self):
        def test_tariff_in_list(**params:dict):
            tariff_list = self.default_admin_client.tariff.list(**params)
            self.search_tariff_in_list(self.tariff, tariff_list)

        test_tariff_in_list()
        test_tariff_in_list(name=self.tariff['localized_name']['en'])
        test_tariff_in_list(name=self.tariff['localized_name']['ru'])
        test_tariff_in_list(description=self.tariff['description'])
        test_tariff_in_list(currency=self.tariff['currency'])
        test_tariff_in_list(parent=None)

    def test_tariff_update_description(self):
        new_description = entities.Tariff(self).basic_name('Описание')
        self.tariff = self.default_admin_client.tariff.update(self.tariff['tariff_id'], description=new_description)
        self.assertEqual(self.tariff['description'], new_description)
        self.tariff = self.default_admin_client.tariff.get(self.tariff['tariff_id'])
        self.assertEqual(self.tariff['description'], new_description)

    def test_tariff_update_name(self):
        new_name = entities.Tariff(self).localized_name()
        self.tariff = self.default_admin_client.tariff.update(self.tariff['tariff_id'], localized_name=new_name)
        self.assertDictEqual(self.tariff['localized_name'], new_name)
        self.tariff = self.default_admin_client.tariff.get(self.tariff['tariff_id'])
        self.assertDictEqual(self.tariff['localized_name'], new_name)

        new_name = entities.Tariff(self).localized_name()
        self.tariff = self.default_admin_client.tariff.update(self.tariff['tariff_id'], localized_name=new_name)
        self.assertDictEqual(self.tariff['localized_name'], new_name)
        self.tariff = self.default_admin_client.tariff.get(self.tariff['tariff_id'])
        self.assertDictEqual(self.tariff['localized_name'], new_name)

    def test_trariff_update_currency(self):
        new_currency = 'USD'
        self.tariff = self.default_admin_client.tariff.update(self.tariff['tariff_id'], currency=new_currency)
        self.assertEqual(self.tariff['currency'], new_currency)

    def test_trariff_update_services(self):
        new_service = {'service_id': next(self.get_immutable_services()), 'price': '125'}
        self.tariff = self.default_admin_client.tariff.update(self.tariff['tariff_id'], services=[new_service])
        self.assertIn(new_service['price'], self.tariff['services'][0]['price'])
        self.assertEqual(self.tariff['services'][0]['service']['service_id'], new_service['service_id'])


class ImmutableTariffTests(OneTariffTests):
    def setUp(self):
        super().setUp()
        self.tariff = self.create_tariff()

    def test_tariff_immutable(self):
        self.default_admin_client.tariff.update(self.tariff['tariff_id'], description=self.tariff['description'])
        self.default_admin_client.tariff.immutable(self.tariff['tariff_id'])

        history = self.default_admin_client.tariff.get_history(self.tariff['tariff_id'])
        self.search_event_in_history(history, 'immutable')

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.update(self.tariff['tariff_id'], description=self.tariff['description'])


class TariffDeleteTests(OneTariffTests):
    def setUp(self):
        super().setUp()
        self.tariff = self.create_tariff()

    def test_tariff_delete(self):
        self.default_admin_client.tariff.delete(self.tariff['tariff_id'])

        history = self.default_admin_client.tariff.get_history(self.tariff['tariff_id'])
        self.search_event_in_history(history, 'delete')

        with self.assertRaisesHTTPError(409):
            self.default_admin_client.tariff.update(self.tariff['tariff_id'], description=self.tariff['description'])


class TariffParentTests(OneTariffTests):
    def setUp(self):
        super().setUp()
        self.parent_tariff = self.create_tariff()

    def test_tariff_create_invalid_parent(self):
        with self.assertRaisesHTTPError(404):
            self.create_tariff(parent_id=112985791285)

    def test_tariff_create_invalid_currency(self):
        with self.assertRaisesHTTPError(409):
            self.create_tariff(parent_id=self.parent_tariff['tariff_id'], currency='USD')

    def test_tariff_create_with_parent(self):
        tariff = self.create_tariff(parent_id=self.parent_tariff['tariff_id'])
        self.assertEqual(tariff['parent_id'], self.parent_tariff['tariff_id'])

    def test_tariff_list_with_parent(self):
        tariff = self.create_tariff(parent_id=self.parent_tariff['tariff_id'])
        tariff_list = self.default_admin_client.tariff.list(parent=self.parent_tariff['tariff_id'])
        self.search_tariff_in_list(tariff, tariff_list)