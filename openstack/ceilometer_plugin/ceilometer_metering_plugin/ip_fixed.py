import collections
import netaddr


from oslo_log import log
from oslo_config import cfg
from oslo_utils import timeutils

from neutronclient.common import exceptions as neutron_exc

from ceilometer.agent import plugin_base
from ceilometer import nova_client, neutron_client
from ceilometer import sample
from ceilometer.i18n import _


from pprint import pformat, pprint

LOG = log.getLogger(__name__)


class FitterFixedIPPollster(plugin_base.PollsterBase):

    @property
    def default_discovery(self):
        return 'local_instances'

    def list_resources_with_long_filters(self, list_method, filter_attr, filter_values, **params):
        """List neutron resources with handling RequestURITooLong exception.

        If filter parameters are long, list resources API request leads to
        414 error (URL is too long). For such case, this method split
        list parameters specified by a list_field argument into chunks
        and call the specified list_method repeatedly.

        :param list_method: Method used to retrieve resource list.
        :param filter_attr: attribute name to be filtered. The value corresponding
            to this attribute is specified by "filter_values".
            If you want to specify more attributes for a filter condition,
            pass them as keyword arguments like "attr2=values2".
        :param filter_values: values of "filter_attr" to be filtered.
            If filter_values are too long and the total URI lenght exceed the
            maximum lenght supported by the neutron server, filter_values will
            be split into sub lists if filter_values is a list.
        :param params: parameters to pass a specified listing API call
            without any changes. You can specify more filter conditions
            in addition to a pair of filter_attr and filter_values.
        """
        try:
            params[filter_attr] = filter_values
            return list_method(**params)
        except neutron_exc.RequestURITooLong as uri_len_exc:
            # The URI is too long because of too many filter values.
            # Use the excess attribute of the exception to know how many
            # filter values can be inserted into a single request.

            # We consider only the filter condition from (filter_attr,
            # filter_values) and do not consider other filter conditions
            # which may be specified in **params.
            if type(filter_values) != list:
                filter_values = [filter_values]

            # Length of each query filter is:
            # <key>=<value>& (e.g., id=<uuid>)
            # The length will be key_len + value_maxlen + 2
            all_filter_len = sum(len(filter_attr) + len(val) + 2
                                 for val in filter_values)
            allowed_filter_len = all_filter_len - uri_len_exc.excess

            val_maxlen = max(len(val) for val in filter_values)
            filter_maxlen = len(filter_attr) + val_maxlen + 2
            chunk_size = allowed_filter_len / filter_maxlen

            resources = []
            for i in range(0, len(filter_values), chunk_size):
                params[filter_attr] = filter_values[i:i + chunk_size]
                resources.extend(list_method(**params))
            return resources

    def port_list(self, **params):
        ports = self.neutron.list_ports(**params).get('ports')
        return ports

    def subnet_list(self, **params):
        subnets = self.neutron.list_subnets(**params).get('subnets')
        return [s for s in subnets]

    def network_list(self, **params):
        networks = self.neutron.list_networks(**params).get('networks')
        # Get subnet list to expand subnet info in network list.
        subnets = self.subnet_list()
        subnet_dict = dict([(s['id'], s) for s in subnets])
        # Expand subnet list from subnet_id to values.
        for n in networks:
            # Due to potential timing issues, we can't assume the subnet_dict data
            # is in sync with the network data.
            n['subnets'] = [subnet_dict[s] for s in n.get('subnets', []) if
                            s in subnet_dict]
        return [n for n in networks]

    def list(self, all_tenants=False, **search_opts):
        if not all_tenants:
            tenant_id = self.request.user.tenant_id
            # In Neutron, list_floatingips returns Floating IPs from
            # all tenants when the API is called with admin role, so
            # we need to filter them with tenant_id.
            search_opts['tenant_id'] = tenant_id
            port_search_opts = {'tenant_id': tenant_id}
        else:
            port_search_opts = {}
        fips = self.neutron.list_floatingips(**search_opts)
        fips = fips.get('floatingips')
        # Get port list to add instance_id to floating IP list
        # instance_id is stored in device_id attribute
        ports = self.port_list(**port_search_opts)
        port_dict = collections.OrderedDict([(p['id'], p) for p in ports])
        for fip in fips:
            self._set_instance_info(fip, port_dict.get(fip['port_id']))
        return [fip for fip in fips]

    def port_get(self, port_id, **params):
        port = self.neutron.show_port(port_id, **params).get('port')
        return port

    def _get_instance_type_from_device_owner(self, device_owner):
        for key, value in self.device_owner_map.items():
            if device_owner.startswith(key):
                return value
        return device_owner

    def _set_instance_info(self, fip, port=None):
        if fip['port_id']:
            if not port:
                port = self.port_get(fip['port_id'])
            fip['instance_id'] = port['device_id']
            fip['instance_type'] = self._get_instance_type_from_device_owner(
                port['device_owner'])
        else:
            fip['instance_id'] = None
            fip['instance_type'] = None

    def _server_get_addresses(self, server, ports, floating_ips, network_names):
        def _format_address(mac, ip, type, device_id, port_id):
            try:
                version = netaddr.IPAddress(ip).version
            except Exception as e:
                error_message = 'Unable to parse IP address %s.' % ip
                pprint(error_message)
                raise e
            return {u'OS-EXT-IPS-MAC:mac_addr': mac,
                    u'version': version,
                    u'addr': ip,
                    u'OS-EXT-IPS:type': type,
                    u'device_id': device_id,
                    u'port_id': port_id}

        addresses = collections.defaultdict(list)
        instance_ports = ports.get(server.id, [])
        for port in instance_ports:
            network_name = network_names.get(port['network_id'])
            if network_name is not None:
                for fixed_ip in port['fixed_ips']:
                    addresses[network_name].append(
                        _format_address(port['mac_address'],
                                        fixed_ip['ip_address'],
                                        u'fixed',
                                        port['device_id'],
                                        port['id']))
                port_fips = floating_ips.get(port['id'], [])
                for fip in port_fips:
                    addresses[network_name].append(
                        _format_address(port['mac_address'],
                                        fip['floating_ip_address'],
                                        u'floating',
                                        port['device_id'],
                                        port['id']))
        return dict(addresses)

    def get_samples(self, manager, cache, resources):
        self.neutron = neutron_client.Client().client
        for server in resources:
            search_opts = {'device_id': server.id}
            ports = self.port_list(**search_opts)

            networks = self.list_resources_with_long_filters(
                self.network_list, 'id', set([port['network_id'] for port in ports]))

            # Map instance to its ports
            instances_ports = collections.defaultdict(list)
            for port in ports:
                instances_ports[port['device_id']].append(port)

            # Map network id to its name
            network_names = dict(((network['id'], network['name']) for network in networks))

            try:
                addresses = self._server_get_addresses(server, instances_ports, {}, network_names)
            except Exception as e:
                LOG.info("[FitterFixedIPPollster] Error: %s" % e)
            else:
                server.addresses = addresses

            for network_name, nets in server.addresses.items():
                for net in nets:
                    yield sample.Sample(
                            name='ip.fixed',
                            unit='ip',
                            type=sample.TYPE_GAUGE,
                            volume=1,
                            user_id=server.user_id,
                            project_id=server.tenant_id,
                            resource_id=net['port_id'],
                            timestamp=timeutils.utcnow().isoformat(),
                            resource_metadata={
                                'address': net['addr'],
                            }
                    )
