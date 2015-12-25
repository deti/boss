from tests.base import TestCaseApi
from mock import patch
from model import db, Tenant as ModelTenant, Customer


class TestStat(TestCaseApi):
    def verify_metric(self, metric_name, expected_value):
        from statistics import BaseStatistics

        for metric, (value, timestamp) in BaseStatistics.client.messages:
            if metric == metric_name:
                self.assertEqual(value, expected_value, "Value for metric '%s' is not valid." % metric)
                return

        metrics = [m for m, _ in BaseStatistics.client.messages]
        self.assertFalse("No messages found for metric %s. Current metrics %s" % (metric_name, ", ".join(metrics)))

    @patch("os_interfaces.openstack_wrapper.openstack.get_ceilometer_samples", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_nova_limits", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_tenants", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_snapshots", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_nova_flavors", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_nova_servers", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_floating_ips", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_images", return_value=None)
    @patch("os_interfaces.openstack_wrapper.openstack.get_volumes", return_value=None)
    def test_hour_stat(self, wrp_get_volumes, wrp_get_images, wrp_get_floating_ips,
                       wrp_get_nova_servers, wrp_get_nova_flavors, wrp_get_snapshots,
                       wrp_get_tenants, wrp_get_nova_limits, wrp_get_ceilometer_samples):
        self.create_tariff("stat")
        self.create_customer("one@mail.ru")

        blocked = self.create_customer("blocked@mail.ru")
        self.admin_client.customer.block(blocked["customer_id"])

        entity = self.create_customer("legal@mail.ru")
        self.admin_client.customer.update(entity["customer_id"], customer_type="entity")
        customer_info = self.create_customer("prod@mail.ru", make_prod=True)

        tenant = ModelTenant.create("fake tenant_id", "fake tenant")
        customer = Customer.get_by_id(customer_info["customer_id"])
        customer.os_tenant_id = tenant.tenant_id
        db.session.add(tenant)
        db.session.flush()

        deleted = self.create_customer("deleted@mail.ru", make_prod=True)
        self.admin_client.customer.delete(deleted["customer_id"])

        from task.notifications import hour_stats
        from keystoneclient.v2_0.tenants import Tenant
        from novaclient.v2.flavors import Flavor
        from novaclient.v2.servers import Server
        from cinderclient.v2.volume_snapshots import Snapshot
        from cinderclient.v2.volumes import Volume
        from ceilometerclient.v2.samples import Sample

        info_flavors = [
            {'OS-FLV-DISABLED:disabled': False,
             'OS-FLV-EXT-DATA:ephemeral': 0,
             'disk': 30,
             'id': 'flavor_id_1',
             'links': [{
                           'href': 'http://openstack.org:8774/v2/2a870d56e2b9411a86fd1736f2217c10/flavors/0316748f-a62f-49ce-a5fe-22e84fb9ad62',
                           'rel': 'self'},
                       {
                           'href': 'http://openstack.org:8774/2a870d56e2b9411a86fd1736f2217c10/flavors/0316748f-a62f-49ce-a5fe-22e84fb9ad62',
                           'rel': 'bookmark'}],
             'name': 'Medium',
             'os-flavor-access:is_public': False,
             'ram': 8192,
             'rxtx_factor': 1.0,
             'swap': '',
             'vcpus': 2},

            {'OS-FLV-DISABLED:disabled': False,
             'OS-FLV-EXT-DATA:ephemeral': 0,
             'disk': 30,
             'id': 'flavor_id_2',
             'links': [{
                           'href': 'http://openstack.ru:8774/v2/2a870d56e2b9411a86fd1736f2217c10/flavors/25e56f22-0ead-41d3-8485-e07af3114de0',
                           'rel': 'self'},
                       {
                           'href': 'http://openstack.ru:8774/2a870d56e2b9411a86fd1736f2217c10/flavors/25e56f22-0ead-41d3-8485-e07af3114de0',
                           'rel': 'bookmark'}],
             'name': 'M.Large',
             'os-flavor-access:is_public': False,
             'ram': 24576,
             'rxtx_factor': 1.0,
             'swap': '',
             'vcpus': 4}
        ]

        info_servers = [
            {'OS-DCF:diskConfig': 'AUTO',
             'OS-EXT-AZ:availability_zone': 'zone',
             'OS-EXT-SRV-ATTR:host': 'qk-9',
             'OS-EXT-SRV-ATTR:hypervisor_hostname': 'qk-9.domain.tld',
             'OS-EXT-SRV-ATTR:instance_name': 'instance-00000ef3',
             'OS-EXT-STS:power_state': 1,
             'OS-EXT-STS:task_state': None,
             'OS-EXT-STS:vm_state': 'active',
             'OS-SRV-USG:launched_at': '2015-10-01T20:23:32.000000',
             'OS-SRV-USG:terminated_at': None,
             'accessIPv4': '',
             'accessIPv6': '',
             'addresses': {'Internet-IPs': [{'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:e7:13:b3',
                                             'OS-EXT-IPS:type': 'fixed',
                                             'addr': '192.168.19.63',
                                             'version': 4}]},
             'config_drive': '',
             'created': '2015-10-01T20:23:15Z',
             'flavor': {
                 'id': 'flavor_id_1',
                 'links': [{
                               'href': 'http://openstack.ru:8774/2a870d56e2b9411a86fd1736f2217c10/flavors/6214ea5e-8d51-4025-885c-e14821b220cc',
                               'rel': 'bookmark'}]},
             'hostId': 'cb111a482618c143ca7a28c87ff0a93a1fb19283192509ac22c32af0',
             'id': '4eda7eb2-e1c9-4f92-b32f-663c11d2deb0',
             'image': '',
             'key_name': None,
             'links': [{
                           'href': 'http://openstack.ru:8774/v2/2a870d56e2b9411a86fd1736f2217c10/servers/4eda7eb2-e1c9-4f92-b32f-663c11d2deb0',
                           'rel': 'self'},
                       {
                           'href': 'http://openstack.ru:8774/2a870d56e2b9411a86fd1736f2217c10/servers/4eda7eb2-e1c9-4f92-b32f-663c11d2deb0',
                           'rel': 'bookmark'}],
             'metadata': {},
             'name': 'active_test',
             'os-extended-volumes:volumes_attached': [{'id': '115feaa7-1126-461d-ad60-067da6dff7c9'}],
             'progress': 0,
             'security_groups': [{'name': 'default'}],
             'status': 'ACTIVE',
             'tenant_id': 'tenant_id_1',
             'updated': '2015-10-01T20:23:32Z',
             'user_id': '25640457f00a485698caabf72bba5f8a'},

            {'OS-DCF:diskConfig': 'AUTO',
             'OS-EXT-AZ:availability_zone': 'zone',
             'OS-EXT-SRV-ATTR:host': 'qk-13',
             'OS-EXT-SRV-ATTR:hypervisor_hostname': 'qk-13.domain.tld',
             'OS-EXT-SRV-ATTR:instance_name': 'instance-00000ef0',
             'OS-EXT-STS:power_state': 1,
             'OS-EXT-STS:task_state': None,
             'OS-EXT-STS:vm_state': 'active',
             'OS-SRV-USG:launched_at': '2015-10-01T20:21:17.000000',
             'OS-SRV-USG:terminated_at': None,
             'accessIPv4': '',
             'accessIPv6': '',
             'addresses': {
                 'Internet-IPs': [{'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:c6:e1:ac',
                                   'OS-EXT-IPS:type': 'fixed',
                                   'addr': '192.169.19.62',
                                   'version': 4}]},
             'config_drive': '',
             'created': '2015-10-01T20:21:01Z',
             'flavor': {'id': 'flavor_id_2',
                        'links': [
                            {
                                'href': 'http://openstack.ru:8774/2a870d56e2b9411a86fd1736f2217c10/flavors/6214ea5e-8d51-4025-885c-e14821b220cc',
                                'rel': 'bookmark'}
                        ]},
             'hostId': 'ccf318ebe253336d47f9bc105c723af000579aa2bc3111262e43e032',
             'id': 'c7856a12-a749-47f2-8c7a-e4ee6e310ef6',
             'image': '',
             'key_name': 'testtesttest',
             'links': [{
                           'href': 'http://openstack.ru:8774/v2/2a870d56e2b9411a86fd1736f2217c10/servers/c7856a12-a749-47f2-8c7a-e4ee6e310ef6',
                           'rel': 'self'},
                       {
                           'href': 'http://openstack.ru:8774/2a870d56e2b9411a86fd1736f2217c10/servers/c7856a12-a749-47f2-8c7a-e4ee6e310ef6',
                           'rel': 'bookmark'}],
             'metadata': {},
             'name': 'testtesttest',
             'os-extended-volumes:volumes_attached': [{'id': 'eac9cfdf-6f88-4ab9-b005-0e4f2534bc08'}],
             'progress': 0,
             'security_groups': [{'name': 'default'}],
             'status': 'stopped',
             'tenant_id': 'tenant_id_2',
             'updated': '2015-10-01T20:21:18Z',
             'user_id': '25640457f00a485698caabf72bba5f8a'}
        ]

        info_floating_ips = [
            {'fixed_ip_address': None,
             'floating_ip_address': '192.168.122.220',
             'floating_network_id': '14d12e05-6e0f-4b1c-b8cd-43747eb5b8c5',
             'id': '9a31e9ff-6b23-43e6-afad-ddd3ba194597',
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
             'status': 'UP',
             'tenant_id': 'd31e2dbfe716428daddbd4631bb73ab0'}]

        info_images = [
            {
                'checksum': 'ee1eca47dc88f4879d8a229cc70a07c6',
                'container_format': 'bare',
                'created_at': '2015-08-05T10:24:00Z',
                'disk_format': 'qcow2',
                'file': '/v2/images/cf70343a-54a7-46e8-9707-330f149d16ef/file',
                'id': 'cf70343a-54a7-46e8-9707-330f149d16ef',
                'min_disk': 0,
                'min_ram': 0,
                'name': 'cirros-0.3.4-x86_64',
                'owner': '514c60f95d9240508be98d1bf20fdccb',
                'protected': False,
                'schema': '/v2/schemas/image',
                'size': 5,
                'status': 'active',
                'tags': [],
                'updated_at': '2015-08-05T10:24:00Z',
                'virtual_size': None,
                'visibility': 'public'
            },
            {
                'checksum': 'ee1eca47dc88f4879d8a229cc70a07c6',
                'container_format': 'bare',
                'created_at': '2015-08-05T10:24:00Z',
                'disk_format': 'qcow2',
                'file': '/v2/images/cf70343a-54a7-46e8-9707-330f149d16ef/file',
                'id': 'cf70343a-54a7-46e8-9707-330f149d16ef',
                'min_disk': 0,
                'min_ram': 0,
                'name': 'cirros-0.3.4-x86_64',
                'owner': '514c60f95d9240508be98d1bf20fdccb',
                'protected': False,
                'schema': '/v2/schemas/image',
                'size': 7,
                'status': 'active',
                'tags': [],
                'updated_at': '2015-08-05T10:24:00Z',
                'virtual_size': None,
                'visibility': 'private'
            }]
        info_volumes = [
            {
                'attachments': [],
                'availability_zone': 'nova',
                'bootable': 'false',
                'consistencygroup_id': None,
                'created_at': '2015-10-08T15:24:22.000000',
                'description': None,
                'encrypted': False,
                'id': 'a5514296-4c70-426c-ba74-3e1ffc29bffc',
                'links': [
                    {
                        'href': 'http://192.168.3.101:8776/v2/514c60f95d9240508be98d1bf20fdccb/volumes/a5514296-4c70-426c-ba74-3e1ffc29bffc',
                        'rel': 'self'},
                    {
                        'href': 'http://192.168.3.101:8776/514c60f95d9240508be98d1bf20fdccb/volumes/a5514296-4c70-426c-ba74-3e1ffc29bffc',
                        'rel': 'bookmark'}],
                'metadata': {},
                'multiattach': False,
                'name': 'denis_test_volume_1',
                'os-vol-host-attr:host': 'ubuntu-kilo#GlusterFS',
                'os-vol-mig-status-attr:migstat': None,
                'os-vol-mig-status-attr:name_id': None,
                'os-vol-tenant-attr:tenant_id': 'aee181ad99394b9e81ecad5d61d09261',
                'os-volume-replication:driver_data': None,
                'os-volume-replication:extended_status': None,
                'replication_status': 'disabled',
                'size': 7,
                'snapshot_id': None,
                'source_volid': None,
                'status': 'available',
                'user_id': '5f796d5bee7f424180c6ba79f55811fe',
                'volume_type': None
            },
            {'attachments': [{'attachment_id': '6464d0e4-7bfa-4284-87bd-85d151e4fdfd',
                              'device': '/dev/vda',
                              'host_name': None,
                              'id': '51e36e6b-aa99-4adc-8f50-e6066a8c885c',
                              'server_id': 'a96aa81d-c5e9-4b05-8e6d-9db7838cf94d',
                              'volume_id': '51e36e6b-aa99-4adc-8f50-e6066a8c885c'}],
             'availability_zone': 'nova',
             'bootable': 'true',
             'consistencygroup_id': None,
             'created_at': '2015-10-08T14:14:19.000000',
             'description': 'hdisk1 hdisk1 hdisk1',
             'encrypted': False,
             'id': '51e36e6b-aa99-4adc-8f50-e6066a8c885c',
             'links': [{
                           'href': 'http://192.168.3.101:8776/v2/514c60f95d9240508be98d1bf20fdccb/volumes/51e36e6b-aa99-4adc-8f50-e6066a8c885c',
                           'rel': 'self'},
                       {
                           'href': 'http://192.168.3.101:8776/514c60f95d9240508be98d1bf20fdccb/volumes/51e36e6b-aa99-4adc-8f50-e6066a8c885c',
                           'rel': 'bookmark'}],
             'metadata': {'attached_mode': 'rw', 'readonly': 'False'},
             'multiattach': False,
             'name': 'hdisk1',
             'os-vol-host-attr:host': 'ubuntu-kilo#GlusterFS',
             'os-vol-mig-status-attr:migstat': None,
             'os-vol-mig-status-attr:name_id': None,
             'os-vol-tenant-attr:tenant_id': '8e165ea202e346299280cb7afd9ef828',
             'os-volume-replication:driver_data': None,
             'os-volume-replication:extended_status': None,
             'replication_status': 'disabled',
             'size': 9,
             'snapshot_id': None,
             'source_volid': None,
             'status': 'in-use',
             'user_id': '392b8565a7ad497793d6bd826db6dbc9',
             'volume_image_metadata': {'checksum': 'ee1eca47dc88f4879d8a229cc70a07c6',
                                       'container_format': 'bare',
                                       'disk_format': 'qcow2',
                                       'image_id': 'cf70343a-54a7-46e8-9707-330f149d16ef',
                                       'image_name': 'cirros-0.3.4-x86_64',
                                       'min_disk': '0',
                                       'min_ram': '0',
                                       'size': '13287936'}, }
        ]
        info_snapshots = [
            {
                'created_at': '2015-10-08T15:25:00.000000',
                'description': '',
                'id': '055f5dc8-2224-47eb-8a55-9c3ecf2f74a0',
                'metadata': {},
                'name': 'test_snapshot_1',
                'os-extended-snapshot-attributes:progress': '100%',
                'os-extended-snapshot-attributes:project_id': 'aee181ad99394b9e81ecad5d61d09261',
                'size': 3,
                'status': 'available',
                'volume_id': 'a5514296-4c70-426c-ba74-3e1ffc29bffc'
            }, {
                'created_at': '2015-10-08T15:25:00.000000',
                'description': '',
                'id': '055f5dc8-2224-47eb-8a55-9c3ecf2f74a0',
                'metadata': {},
                'name': 'test_snapshot_2',
                'os-extended-snapshot-attributes:progress': '100%',
                'os-extended-snapshot-attributes:project_id': 'aee181ad99394b9e81ecad5d61d09261',
                'size': 5,
                'status': 'available',
                'volume_id': 'a5514296-4c70-426c-ba74-3e1ffc29bffc'
            }
        ]
        info_tenants = [
            {'description': 'Unit test tenant - 1',
             'enabled': True,
             'id': 'tenant_id_1',
             'name': 'tenant_name_1'},
            {'description': 'Unit test tenant - 2',
             'enabled': True,
             'id': 'tenant_id_2',
             'name': 'tenant_name_2'},
            {'description': 'Unit test tenant - 3',
             'enabled': True,
             'id': 'tenant_id_3',
             'name': 'tenant_name_3'},
        ]
        info_nova_limits = {
            'maxImageMeta': 128,
            'maxPersonality': 5,
            'maxPersonalitySize': 10240,
            'maxSecurityGroupRules': 20,
            'maxSecurityGroups': 10,
            'maxServerGroupMembers': 10,
            'maxServerGroups': 10,
            'maxServerMeta': 128,
            'maxTotalCores': 20,
            'maxTotalFloatingIps': 10,
            'maxTotalInstances': 20,
            'maxTotalKeypairs': 10,
            'maxTotalRAMSize': 20480,
            'totalCoresUsed': 1,
            'totalFloatingIpsUsed': 0,
            'totalInstancesUsed': 1,
            'totalRAMUsed': 8192,
            'totalSecurityGroupsUsed': 1,
            'totalServerGroupsUsed': 0
        }

        info_bandwidth = [
            {'id': 'c9510474-5e04-11e5-920d-fa163e4b35b4',
             'metadata': {'fref': 'None',
                          'instance_id': '1b02a1c2-7a6e-404a-b355-d2840d295677',
                          'instance_type': 'ef9a407d-742d-4f23-9055-decbccb143d9',
                          'mac': 'fa:16:3e:9e:18:12',
                          'name': 'tap345a6b63-eb'},
             'meter': 'network.incoming.bytes',
             'project_id': '03926f96177e4df9a0fc5c77f6e674d8',
             'recorded_at': '2015-09-18T12:57:15.769000',
             'resource_id': 'instance-00000018-1b02a1c2-7a6e-404a-b355-d2840d295677-tap345a6b63-eb',
             'source': 'openstack',
             'timestamp': '2015-09-18T12:57:15',
             'type': 'cumulative',
             'unit': 'B',
             'user_id': 'c1ef3d08d9694acb8740ccb66d0ba945',
             'volume': 11.0
             },
        ]

        wrp_get_ceilometer_samples.return_value = [Sample(None, s) for s in info_bandwidth]
        wrp_get_images.return_value = info_images
        wrp_get_floating_ips.return_value = info_floating_ips
        wrp_get_tenants.return_value = [Tenant(None, t) for t in info_tenants]
        wrp_get_nova_servers.return_value = [Server(None, s) for s in info_servers]
        wrp_get_nova_flavors.return_value = [Flavor(None, f) for f in info_flavors]
        wrp_get_volumes.return_value = [Volume(None, volume) for volume in info_volumes]
        wrp_get_snapshots.return_value = [Snapshot(None, snapshot) for snapshot in info_snapshots]
        wrp_get_nova_limits.return_value = info_nova_limits

        # Run stat collection
        hour_stats()

        expected_stats = {
            "stats.flavor.total": 2,
            "stats.flavor.Medium": 1,

            'stats.ip.floating.active_customer': 6,
            'stats.ip.floating.blocked_customer': 2,
            'stats.ip.floating.customer_mode-production': 2,
            'stats.ip.floating.customer_mode-test': 6,
            'stats.ip.floating.customer_type-entity': 2,
            'stats.ip.floating.customer_type-private': 6,
            'stats.ip.floating.ip_status-DOWN': 4,
            'stats.ip.floating.ip_status-UP': 4,
            'stats.ip.floating.total': 8,

            'stats.storage.image.total': 2,
            'stats.storage.image.total_size': 12,
            'stats.storage.image.visibility-public': 1,
            'stats.storage.image.visibility-private': 1,
            'stats.storage.image.status-active': 2,

            'stats.storage.volume.total': 2,
            'stats.storage.volume.total_size': 16,
            'stats.storage.volume.volume-bootable': 2,
            'stats.storage.volume.status-available': 1,
            'stats.storage.volume.status-in-use': 1,

            'stats.storage.snapshots.total': 2,
            'stats.storage.snapshots.total_size': 8,
            'stats.storage.snapshots.available': 2,

            'stats.resources.totalRAMUsed': 8192*1,
            'stats.resources.totalCoresUsed': 1,
            'stats.resources.flavor.Medium.ram': 8192,
            'stats.resources.flavor.Medium.vcpus': 2,

            'stats.network.outgoing.bytes': info_bandwidth[0]['volume'] * len(info_tenants),
            'stats.network.incoming.bytes': info_bandwidth[0]['volume'] * len(info_tenants),

        }
        for k, v in expected_stats.items():
            self.verify_metric(k, v)
