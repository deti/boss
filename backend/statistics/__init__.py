import conf
import graphiti
import logbook
from model import Customer
from os_interfaces.openstack_wrapper import openstack, VM_STATE
from collections import Counter
from arrow import utcnow


class FakeGraphitiClient(graphiti.Client):
    def send(self, path, value, timestamp=None):
        path = graphiti.client.normalize_path(path)
        self.messages.append((path, (value, timestamp)))

    def _send(self):
        return True


class EmptyGraphitiClient(graphiti.Client):
    def send(self, path, value, timestamp=None):
        pass


class BaseStatistics:
    if conf.test:
        client = FakeGraphitiClient(conf.statistics.carbon_host)
    else:
        client = graphiti.Client(conf.statistics.carbon_host) if conf.statistics.carbon_host \
            else EmptyGraphitiClient("")
    prefix = None
    base_prefix = conf.statistics.base_prefix

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def join(values, delimiter="."):
        return delimiter.join(filter(None, values))

    def send(self, metrics, timestamp=None, prefix=None):
        for name, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_name = self.join((self.base_prefix, self.prefix, prefix, name))
                self.client.send(metric_name, value, timestamp)
            elif isinstance(value, dict):
                self.send(value, timestamp, prefix=self.join((prefix, name)))
            elif value is None:
                pass
            else:
                logbook.error("Invalid value type for metric {}: {} {}", name, type(value), value)

    def stat(self):
        raise NotImplemented()

    def tick(self):
        logbook.debug("Try to prepare stats {}", str(self))
        stat = self.stat()
        logbook.info("Statistics {}: {}", self, stat)
        if stat:
            self.send(stat)


class CustomerStats(BaseStatistics):
    prefix = "customer"

    def stat(self):
        return Customer.customers_stat()


class FlavorStats(BaseStatistics):
    prefix = "flavor"

    def stat(self):
        servers = openstack.get_nova_servers()
        flavors = openstack.get_nova_flavors()
        logbook.debug("Configured {} flavors", len(flavors))
        logbook.info("Total servers: {}", len(servers))

        flavor_names = {flavor.id: flavor.name for flavor in flavors}

        result = Counter()
        running = 0
        for server in servers:
            if not VM_STATE.is_running(server.status):
                continue

            flavor_id = server.flavor["id"]
            flavor_name = flavor_names.get(flavor_id, "unknown")
            result[flavor_name] += 1
            running += 1

        result["total"] = len(servers)
        result["total_running"] = running
        return result


class IPsStats(BaseStatistics):
    prefix = "ip.floating"

    def stat(self):
        result = Counter()
        total_ips = 0
        for customer in Customer.query.filter(Customer.deleted == None):
            tenant_id = customer.os_tenant_id
            ips = openstack.get_floating_ips(tenant_id=tenant_id)
            total_ips += len(ips)
            for ip in ips:
                result['customer_type-%s' % customer.customer_type] += 1
                result['customer_mode-%s' % customer.customer_mode] += 1
                if customer.blocked:
                    result['blocked_customer'] += 1
                else:
                    result['active_customer'] += 1
                result['ip_status-%s' % ip['status']] += 1
        result['total'] = total_ips
        return result


class StorageImageStats(BaseStatistics):
    prefix = "storage.image"

    def stat(self):
        result = Counter()
        total_size = 0
        total_images = 0
        images = openstack.get_images()
        for image in images:
            total_images += 1
            if image['size']:
                total_size += image['size']
            result['status-%s' % image['status']] += 1
            result['visibility-%s' % image['visibility']] += 1
        result['total'] = total_images
        result['total_size'] = total_size
        return result


class StorageVolumeStats(BaseStatistics):
    prefix = "storage.volume"

    def stat(self):
        result = Counter()
        total_size = 0
        volumes = openstack.get_volumes()
        for volume in volumes:
            total_size += volume.size
            if volume.bootable:
                result['volume-bootable'] += 1
            result['status-%s' % volume.status] += 1
        result['total'] = len(volumes)
        result['total_size'] = total_size
        return result


class StorageSnapshotStats(BaseStatistics):
    prefix = "storage.snapshots"

    def stat(self):
        result = Counter()
        total_size = 0
        snapshots = openstack.get_snapshots()
        for snapshot in snapshots:
            total_size += snapshot.size
            result[snapshot.status] += 1
        result['total'] = len(snapshots)
        result['total_size'] = total_size
        return result


class ResourceStats(BaseStatistics):
    prefix = "resources"

    def stat(self):
        result = Counter()
        flavors = openstack.get_nova_flavors()
        id2flavor = {flavor.id: flavor for flavor in flavors}

        for tenant_id in Customer.active_tenants():
            servers = openstack.get_nova_servers(tenant_id=tenant_id)
            for server in servers:
                if not server.status == 'ACTIVE':
                    continue
                server_flavor_id = server.flavor['id']
                server_flavor = id2flavor.get(server_flavor_id)
                if server_flavor:
                    server_flavor_name = server_flavor.name
                    result['flavor.%s.vcpus' % server_flavor_name] += server_flavor.vcpus
                    result['flavor.%s.ram' % server_flavor_name] += server_flavor.ram
                else:
                    logbook.error("Server {} in tenant {} has unknown flavor: {}", server, tenant_id, server.flavor)

            # Check total resource usage for each tenant
            limits = openstack.get_nova_limits(tenant_id=tenant_id)
            for k, v in limits.items():
                if v > 0 and k in ['totalCoresUsed', 'totalRAMUsed']:
                    result[k] += v

        return result


class NetworkStats(BaseStatistics):
    prefix = "network"

    def stat(self):
        incoming_bytes = 0
        outgoing_bytes = 0
        tenants = openstack.get_tenants()
        for tenant in tenants:
            q = [
                {'field': 'project', 'op': 'eq', 'value': tenant.id},
                {'field': 'meter', 'op': 'eq', 'value': 'network.incoming.bytes'}
            ]
            samples_in = openstack.get_ceilometer_samples(q, limit=1)
            if samples_in:
                incoming_bytes += samples_in[0].volume

            q = [
                {'field': 'project', 'op': 'eq', 'value': tenant.id},
                {'field': 'meter', 'op': 'eq', 'value': 'network.outgoing.bytes'}
            ]
            samples_out = openstack.get_ceilometer_samples(q, limit=1)
            if samples_out:
                outgoing_bytes += samples_out[0].volume

        result = {
            'incoming.bytes': incoming_bytes,
            'outgoing.bytes': outgoing_bytes}
        return result


class OpenstackUsage(BaseStatistics):
    prefix = "openstack_usage"

    def stat(self):
        from model import Customer
        from memdb.report_cache import ReportCache, ReportId

        billed_tenants = {customer.os_tenant_id: customer for customer in Customer.query
                          if customer.os_tenant_id}
        result_usage = {}
        total = Counter()
        unknown_total = Counter()
        tenants = openstack.get_tenants()

        for tenant in tenants:
            tenant_id = tenant.id
            customer = billed_tenants.get(tenant_id)

            if customer:
                username, password = customer.os_username, customer.os_user_password
            else:
                username, password = None, None

            usage = openstack.get_limits(tenant_id, username, password)
            result_usage[tenant_id] = usage

            for key, value in usage.items():
                if value is not None:
                    total[key] += value
                    if customer is None:
                        unknown_total[key] += value
            usage["tenant"] = {"name": tenant.name,
                               "description": tenant.description,
                               "enabled": tenant.enabled}
            if customer is None:
                total["unknown"] += 1
                usage["customer"] = {}
            else:
                usage["customer"] = {"customer_id": customer.customer_id, "email": customer.email,
                                     "type": customer.customer_type, "mode": customer.customer_mode}

        data = {"total": dict(total), "unknown_total": dict(unknown_total),
                "tenant_usage": result_usage,
                "timestamp": utcnow().datetime}
        report_id = ReportId(None, None, "openstack_usage", None, None)
        ReportCache().set_report_aggregated(report_id, data, conf.report.cache_time.report)

        # clean customer value in result, because this info can't be stored in graphite
        for usage in result_usage.values():
            usage["customer"] = {}
            usage["tenant"] = {}
        del data["timestamp"]
        return data

all_stats = {stat.name: stat for stat in (CustomerStats(), FlavorStats(), IPsStats(), StorageImageStats(),
                                          StorageVolumeStats(), StorageSnapshotStats(), ResourceStats(),
                                          NetworkStats(), OpenstackUsage())}
