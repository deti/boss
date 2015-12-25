from tests.base import BaseTestCaseDB
from os_interfaces.openstack_wrapper import openstack
from mock import MagicMock, call


class TestOpenstackWrapper(BaseTestCaseDB):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        pass

    def test_create_network(self):
        network = {
            'name': 'TestNetwork',
            'admin_state_up': True,
            'tenant_id': '123',
            'id': 1
        }
        self.assertEqual(network, openstack.create_network('TestNetwork', '123'))

    def test_create_subnet(self):
        subnet = {
            'network_id': 1,
            'tenant_id': 2,
            'cidr': '10.0.0.1/24',
            'ip_version': 4,
            'dns_nameservers': ['8.8.8.8'],
            'id': 1
        }
        self.assertEqual(subnet, openstack.create_subnet(1, 2, ['8.8.8.8']))

    def test_create_router(self):
        router = {'tenant_id': 2,
                  'external_gateway_info': {
                      'network_id': 1
                  },
                  'id': 1
        }
        self.assertEqual(router, openstack.create_router(2, 1))

    def test_attach_subnet_to_router(self):
        openstack.attach_subnet_to_router(1, 2)
        self.assertEqual([call(1, body={'subnet_id': 2})], openstack.client_neutron.add_interface_router.mock_calls)
