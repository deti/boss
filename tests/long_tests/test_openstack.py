from pprint import pformat
import datetime
import logbook
import novaclient.exceptions
import cinderclient.exceptions
import time
import random
from utils.base import BaseTestCase
from clients import OpenstackClient
from utils.tools import format_backend_datetime, find_first


class OpentackTestBase(BaseTestCase):
    _offsets = set()

    def create_openstack_customer(self, services: list):
        """Create customer for working in openstack, with authorized openstack client"""
        tariff_info = self.create_tariff(services, immutable=True)
        customer_info, _, customer_client = self.create_customer(with_client=True, confirmed=True, need_openstack=True,
                                                                 locale='en', go_prod=True, make_full_prod=True,
                                                                 mailtrap_email=True)
        self.default_admin_client.customer.update(customer_info['customer_id'], tariff=tariff_info['tariff_id'])
        openstack_credentials = self.get_openstack_credentials(customer_info)
        openstack_client = OpenstackClient.init_by_creds(*openstack_credentials)

        return customer_info, customer_client, openstack_client

    def get_default_image(self, openstack_client: OpenstackClient):
        """Return default image object for server creation"""
        image_list = openstack_client.image_list()
        return image_list[0]

    def get_flavor_by_name(self, openstack_client: OpenstackClient, flavor_name:str):
        """Get opentsack flavor by name, case insensitive."""
        flavor_list = openstack_client.flavor_list()
        return self.assertInList(flavor_list, lambda flavor: flavor.human_id.lower() == flavor_name.lower(),
                                 'Flavor with id="{}" not found in flavor list:{}'.format(flavor_name, flavor_list))

    def get_default_network(self, openstack_client: OpenstackClient) -> dict:
        """Return default network dict for server creation"""
        network_list = openstack_client.network_list()['networks']
        return find_first(network_list, lambda network: network['name'] == 'DefaultPrivateNet') or network_list['networks'][0]

    def get_used_quotes(self, customer_client) -> dict:
        """Return formatted used_quotes dict"""
        used_quotas = customer_client.customer.quota_used()['used_quotas']
        result = dict()
        for section_dict in used_quotas:
            for section_name, section_info in section_dict.items():
                for quote_info in section_info:
                    result[quote_info['limit_id']] = quote_info
        return result

    def resource_delete(self, resource, exception:Exception):
        """Delete resource and wait for it's deletion"""
        for r in self.retries(20, 1):
            with r:
                with self.assertRaises(exception):
                    resource.delete()

    def check_server_quote_usage(self, quote_info:dict, flavor, instances:int=1):
        self.assertEqual(quote_info['instances']['value'], instances)
        self.assertEqual(quote_info['cores']['value'], flavor.vcpus*instances)
        self.assertEqual(quote_info['ram']['value'], flavor.ram*instances)

    def check_storage_quote_usage(self, quote_info:dict, volumes:list=None, snapshots:list=None):
        total_size = 0
        if volumes:
            self.assertEqual(quote_info['volumes']['value'], len(volumes))
            total_size += sum(map(lambda volume: volume.size, volumes))
        if snapshots:
            self.assertEqual(quote_info['snapshots']['value'], len(snapshots))
            total_size += sum(map(lambda snapshot: snapshot.size, snapshots))

        if total_size:
            self.assertEqual(quote_info['gigabytes']['value'], total_size)

    def generate_report_time_interval(self, offset:int=None) -> dict:
        make_report_datetime = lambda dt: format_backend_datetime(dt, time_format='%H')

        if offset is None:
            while True:
                offset = random.randint(2, 1000)
                if offset in self._offsets:
                    continue
                self._offsets.add(offset)
                break

        finish_dt = datetime.datetime.utcnow()
        start_dt = finish_dt - datetime.timedelta(hours=offset)
        finish = make_report_datetime(finish_dt)
        start = make_report_datetime(start_dt)
        return {'start': start, 'finish': finish}

    def wait_report(self, customer_client, report_format='json', report_type='detailed', start=None, finish=None):
        if not start or not finish:
            interval = self.generate_report_time_interval()
            start, finish = interval['start'], interval['finish']
        for r in self.retries(30, 1):
            with r:
                report = customer_client.customer.report(start=start, finish=finish, report_format=report_format,
                                                         report_type=report_type)
                if isinstance(report, dict):
                    self.assertEqual(report['status'], 'completed')
                    report = report['report']
                else:
                    self.assertTrue(isinstance(report, bytes))
        return report

    def sleep(self, seconds:int=5):
        time.sleep(seconds)

    def wait_server_status(self, server, status):
        for r in self.retries(60, 1):
            with r:
                server.get()
                self.assertEqual(server.to_dict()['status'], status, str(vars(server)))

    def count_usage(self, service_info:dict, service_usage:dict, delta_offset:datetime.timedelta=None) -> float:
        total = 0
        for (service_id, resource_id), usage_info in service_usage.items():
            service_price = float(service_info[service_id])
            usage_info['delta'] = usage_info['end'] - usage_info['start']
            if delta_offset is not None:
                usage_info['delta'] += delta_offset
            usage_info['hours'] = (usage_info['delta'].seconds // 60) // 60 + 1
            usage_info['price'] = service_price * usage_info['hours'] * usage_info.get('count', 1)
            total += usage_info['price']
        return total

    def resource_start(self, service_usage, service_id, resource_id, count:int=1):
        service_usage[(service_id, resource_id)] = dict(start=datetime.datetime.now(), count=count)

    def resource_stop(self, service_usage, service_id, resource_id):
        service_usage[(service_id, resource_id)]['end'] = datetime.datetime.now()


class TestOpenstack(OpentackTestBase):
    def make_fake_usage(self, customer_id, service_usage, service_id, resource_id, volume=None):
        if volume is None:
            volume = service_usage[(service_id, resource_id)].get('count', 1)
        self.default_admin_client.customer.fake_usage(customer_id,
                                                      self.make_datetime(service_usage[(service_id, resource_id)]['start'] - datetime.timedelta(days=1)),
                                                      self.make_datetime(service_usage[(service_id, resource_id)]['end'] - datetime.timedelta(days=1)),
                                                      service_id, resource_id, volume)

    def test_instance(self):
        service_info = {
            'vm.Nano': 2,
            'vm.Micro': 3,
            'storage.volume': 2,  # Additional Disks and Snapshots
            'net.allocated_ip': 3,  # Bill the allocated Internet IP-addresses (Floating IPs).
        }
        service_usage = dict()

        customer_info, customer_client, openstack_client = self.create_openstack_customer(list(service_info.items()))

        quotas = self.get_used_quotes(customer_client)
        if quotas['floatingip']['max_value'] == 0:
            self.default_admin_client.customer.quote.update(customer_info['customer_id'], {'floatingip': 1})

        server_network = self.get_default_network(openstack_client)
        server_image = self.get_default_image(openstack_client)
        server_flavor = self.get_flavor_by_name(openstack_client, 'nano')

        # create server
        volume_size = 10
        server_block_device_mapping = {
            'uuid': server_image.id,
            'source_type': 'image',
            'destination_type': 'volume',
            'volume_size': volume_size,
            'delete_on_termination': 'True',
            'boot_index': 0
        }
        server = openstack_client.nova_client.servers.create(name=self.create_name(), flavor=server_flavor,
                                                             nics=[{'net-id': server_network['id']}], image=None,
                                                             block_device_mapping_v2=[server_block_device_mapping])
        self.addCleanupBeforeDelete(self.resource_delete, server, novaclient.exceptions.NotFound)
        self.resource_start(service_usage, 'vm.Nano', server.id)
        for r in self.retries(20, 1):
            with r:
                volume_list = openstack_client.cinder_client.volumes.list()
                self.assertGreater(len(volume_list), 0)
        volume = volume_list[0]

        self.resource_start(service_usage, 'storage.volume', volume.id, volume_size)

        self.wait_server_status(server, 'ACTIVE')

        # resize server
        resize_flavor = self.get_flavor_by_name(openstack_client, 'micro')
        logbook.debug('Resizing server [{}] from {} to {}'.format(server.id, server_flavor.human_id, resize_flavor.human_id))
        openstack_client.nova_client.servers.resize(server, resize_flavor)
        self.wait_server_status(server, 'VERIFY_RESIZE')
        openstack_client.nova_client.servers.confirm_resize(server)
        self.wait_server_status(server, 'ACTIVE')

        self.resource_start(service_usage, 'vm.Micro', server.id)
        self.resource_stop(service_usage, 'vm.Nano', server.id)

        # create snapshot
        snapshot = openstack_client.cinder_client.volume_snapshots.create(volume.id, True, self.create_name())
        self.resource_start(service_usage, 'storage.volume', snapshot.id, volume_size)

        # associate floating IP
        floating_ip = openstack_client.nova_client.floating_ips.create(openstack_client.nova_client.floating_ip_pools.list()[0].name)
        self.addCleanupBeforeDelete(floating_ip.delete)

        self.resource_start(service_usage, 'net.allocated_ip', floating_ip.id)

        server.add_floating_ip(floating_ip)
        self.sleep(5)

        # disassociate floating IP
        openstack_client.nova_client.servers.remove_floating_ip(server, floating_ip)

        self.resource_stop(service_usage, 'net.allocated_ip', floating_ip.id)

        self.sleep(5)

        self.resource_delete(snapshot, cinderclient.exceptions.NotFound)
        self.resource_stop(service_usage, 'storage.volume', snapshot.id)

        self.resource_delete(server, novaclient.exceptions.NotFound)
        self.resource_stop(service_usage, 'vm.Micro', server.id)

        self.resource_stop(service_usage, 'storage.volume', volume.id)

        # self.make_fake_usage(customer_info['customer_id'], service_usage, 'vm.Nano', server.id)
        # self.make_fake_usage(customer_info['customer_id'], service_usage, 'vm.Micro', server.id)
        # self.make_fake_usage(customer_info['customer_id'], service_usage, 'storage.volume', volume.id, volume_size*1024*1024*1024)
        # self.make_fake_usage(customer_info['customer_id'], service_usage, 'storage.volume', snapshot.id, volume_size*1024*1024*1024)
        # self.make_fake_usage(customer_info['customer_id'], service_usage, 'net.allocated_ip', floating_ip.id)

        # admin_openstack_client = OpenstackClient()
        # ceilometer_samples = admin_openstack_client.ceilometer_client.new_samples.list(
        #     q=[{'field': 'project_id', 'op': 'eq', 'value': customer_info['os_tenant_id']}])
        # logbook.debug(pformat(ceilometer_samples))

        start = time.time()
        for r in self.retries(60*65, sleep_time=30):
            with r:
                report = self.wait_report(customer_client)
                self.assertGreater(len(report['tariffs']), 0, 'Report is empty')

        logbook.debug('Got report in {} seconds'.format(time.time() - start))
        total_cost = self.count_usage(service_info, service_usage)
        logbook.debug('Total cost:'+str(total_cost))
        logbook.debug('Self counted usage:')
        logbook.debug(pformat(service_usage))

        tariff_usage = report['tariffs'][0]
        self.assertEqual(total_cost, float(tariff_usage['total_cost']))

        usage = tariff_usage['usage']

        for usage_info in usage:
            service_id = usage_info['service_id']
            for resource_id, resource_info in usage_info['resources'].items():
                interval_info = resource_info['intervals'][0]
                self.assertEqual(service_info[service_id], float(usage_info['price']), 'Invalid price for %s' % service_id)
                self.assertEqual(float(interval_info['total_cost']), service_usage[(service_id, resource_id)]['price'])
                logbook.debug('Time usage of {} is report={} our={}'.format(service_id, interval_info['time_usage'],
                                                                            service_usage[(service_id, resource_id)]['delta'].seconds))
                self.assertEqual(interval_info['volume'], service_usage[(service_id, resource_id)].get('count', 1))
