from pprint import pformat
from api_tests.openstack_tests import OpenstackTestBase
import logbook
from clients import OpenstackClient
import unittest


class TestOpenstack(OpenstackTestBase):
    image_human_id = None
    service_id = 'vm.Nano'
    flavor_human_id = service_id.split('.')[1].lower()

    def search_network_in_list(self, network_name, network_list):
        return self.assertInList(network_list, lambda network: network['name'] == network_name,
                                 '{} not found in networks list'.format(network_name))

    def test_networks(self):
        customer_info, _, customer_client = self.create_customer(True, confirmed=True, with_client=True,
                                                                 need_openstack=True, mailtrap_email=True)

        openstack_client = OpenstackClient.init_by_creds(*self.get_openstack_credentials(customer_info))

        networks = openstack_client.network_list()['networks']
        self.assertGreater(len(networks), 0)

        self.search_network_in_list('DefaultPrivateNet', networks)

        network_name = self.create_name()
        network = openstack_client.network_create(name=network_name)['network']
        try:
            self.assertEqual(network['name'], network_name)
            networks = openstack_client.network_list()['networks']
            self.search_network_in_list(network_name, networks)
        finally:
            openstack_client.network_delete(network['id'])

        networks = openstack_client.network_list()['networks']
        with self.assertRaises(AssertionError):
            self.search_network_in_list(network_name, networks)

    @unittest.skip('BOSS-1387')
    def test_server_creation(self):
        existed_default_tariff = self.check_default_tariff()
        if existed_default_tariff:
            self.addCleanupBeforeDelete(self.default_admin_client.tariff.set_default, existed_default_tariff['tariff_id'])
        self.create_tariff([(self.service_id, '123')], set_default=True, immutable=True)

        customer_info, _, customer_client = self.create_customer(confirmed=True, with_client=True,
                                                                 need_openstack=True, mailtrap_email=True)
        openstack_client = OpenstackClient.init_by_creds(*self.get_openstack_credentials(customer_info))

        image_list = openstack_client.image_list()
        if self.image_human_id is None:
            image = image_list[0]
        else:
            image = self.assertInList(image_list, lambda image: image.human_id == self.image_human_id,
                                      'Image with id="{}" not found in image list:{}'.format(self.image_human_id, image_list))

        image_id = image.id
        image_human_id = image.human_id

        flavor_list = openstack_client.flavor_list()
        if self.flavor_human_id is None:
            flavor = flavor_list[0]
        else:
            flavor = self.assertInList(flavor_list, lambda flavor: flavor.human_id == self.flavor_human_id,
                                      'Flavor with id="{}" not found in flavor list:{}'.format(self.flavor_human_id, flavor_list))

        flavor_id = flavor.id
        flavor_human_id = flavor.human_id
        logbook.debug(pformat(flavor.to_dict()))

        network_list = openstack_client.network_list()['networks']
        network_id = network_list[0]['id']
        network_human_id = network_list[0]['name']

        server_name = self.create_name()

        logbook.info('Creating instance image={} flavor={} network={} name={}'.format(image_human_id, flavor_human_id,
                                                                                      network_human_id, server_name))

        server = openstack_client.server_create(server_name, image_id, flavor_id, nics=[{'net-id': network_id}])
        self.addCleanupBeforeDelete(server.delete)

        for r in self.retries(120):
            with r:
                data = openstack_client.nova_client.servers.get(server.id).to_dict()
                logbook.debug(data)
                vm_state = data['OS-EXT-STS:vm_state']
                if vm_state != 'active':
                    if vm_state == 'error':
                        message = 'Error while creating server'
                        if 'fault' in data:
                            message += ': ' + data['fault']['message']
                        raise ValueError(message)
                self.assertEqual(vm_state, 'active', 'Server is not created yet')

        used = customer_client.customer.quota_used()['used_quotas']
        search_in_list = lambda section: next(item[section] for item in used if list(item)[0] == section)
        get = lambda section, limit_id: next(item for item in search_in_list(section) if item['limit_id'] == limit_id)

        self.assertEqual(get('server_group', 'instances')['value'], 1)
        self.assertEqual(get('compute_group', 'cores')['value'], flavor.vcpus)
        self.assertEqual(get('compute_group', 'ram')['value'], flavor.ram)
