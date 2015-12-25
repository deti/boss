"""
Cleans OpenStack from test entities

Usage: openstack_clean [(-u | --unassigned)] [--keyword=<keyword>] [--read-only] [--verbose]

Options:
    -u --unassigned      Deletes not assigned to any tenant entities
    --keyword=<keyword>  Keyword for searching users and tenants [default: $test]
    --read-only          Just display objects which should be removed
    -v --verbose         Output debug messages

"""
import logbook as log

from utils import find_first, setup_backend_logbook
from os_interfaces.openstack_wrapper import openstack
from functools import lru_cache, reduce


@lru_cache()
def get_tenant(tenant_id):
    return openstack.get_tenant(tenant_id)


def ignore_exception(fn):
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            import traceback
            traceback.print_exc()
    return inner


def get_tenants_and_users(keyword):
    id_pairs = []
    all_tenants = openstack.get_tenants()
    tenants = [tenant.id for tenant in all_tenants if keyword in tenant.description]
    for tenant in tenants:
        users = openstack.client_keystone.tenants.list_users(tenant)
        user = users[0].id if users else None
        id_pairs.append((user, tenant))

    all_users = openstack.client_keystone.users.list()
    users = [(user.id, None) for user in all_users
             if keyword in user.name and find_first(id_pairs, lambda x: x[0] == user.id) is None]
    id_pairs.extend(users)

    return id_pairs


def accum_total(accum, resources):
    for resource in resources:
        if accum.get(resource, None):
            accum[resource] += resources[resource]
        else:
            accum[resource] = resources[resource]

    return accum


def delete_by_keyword(keyword, read_only):
    id_pairs = get_tenants_and_users(keyword)
    total_list = []
    for id_pair in id_pairs:
        try:
            deleted = openstack.final_delete(*id_pair)
            total_list.append(deleted)
        except Exception:
            log.warning("Deleting of tenant {} has failed", id_pair, exc_info=True)

    if total_list:
        total = reduce(accum_total, total_list, {})
        total_str = ",".join("%s %s" % (k, total[k]) for k in sorted(total))
        log.info('Deleted {}', total_str)
    else:
        log.info('Nothing to delete by keyword {}', keyword)


@ignore_exception
def delete_floatingips(read_only):
    all_ips = openstack.client_neutron.list_floatingips()['floatingips']
    ips = [ip['id'] for ip in all_ips if not get_tenant(ip['tenant_id'])]

    if ips:
        log.info("Delete unassigned ips: {}", ",".join(ips))
    if not read_only:
        for ip in ips:
            openstack.delete_floating_ip(ip)

    return len(ips)


@ignore_exception
def delete_instances(read_only):
    all_instances = openstack.get_nova_servers()
    instances = [instance for instance in all_instances if not get_tenant(instance.tenant_id)]

    for instance in instances:
        log.info('Deleting unassigned instance {} in tenant {}', instance.id, instance.tenant_id)
        if not read_only:
            openstack.client_nova.servers.delete(instance)

    return len(instances)


@ignore_exception
def delete_volumes(read_only):
    all_volumes = openstack.get_volumes()
    volumes = [volume for volume in all_volumes if not get_tenant(getattr(volume, 'os-vol-tenant-attr:tenant_id'))]
    for volume in volumes:
        log.info('Deleting unassigned volume {}, name: {}, size: {}, image_name: {}. tenant: {}',
                 volume.id, volume.name, volume.size, getattr(volume, "volume_image_metadata", None)["image_name"],
                 getattr(volume, 'os-vol-tenant-attr:tenant_id'))
        if not read_only:
            try:
                openstack.client_cinder.volumes.delete(volume.id)
            except Exception as e:
                log.warning("Can't remove volume {}: {}", volume._info, e)

    return len(volumes)


@ignore_exception
def delete_snapshots(read_only):
    all_snapshots = openstack.get_snapshots()
    snapshots = [snapshot for snapshot in all_snapshots if not get_tenant(snapshot.project_id)]
    for snapshot in snapshots:
        log.info('Deleting unassigned snapshot {}, tenant: {}', snapshot, snapshot.project_id)
        if not read_only:
            try:
                openstack.client_cinder.volume_snapshots.delete(snapshot.id)
            except Exception as e:
                log.warning("Can't remove snapshot {}: {}", snapshot._info, e)

    return len(snapshots)


@ignore_exception
def delete_images(read_only):
    all_images = openstack.get_nova_images()
    images = 0
    for image in all_images:
        tenant_id = image.metadata.get('owner_id', None)
        if tenant_id is not None and not get_tenant(tenant_id):
            log.info('Deleted unassigned image {}', image.id)
            if not read_only:
                openstack.client_nova.images.delete(image.id)
            images += 1

    return images


@ignore_exception
def delete_router(router, read_only):
    info = router["external_gateway_info"]
    ips = [ip["ip_address"] for ip in info["external_fixed_ips"] if ip]
    log.info('Deleting unassigned router {}, network {}, ip {}, tenant {}',
             router["id"], info["network_id"], ",".join(ips), router["tenant_id"])

    search_opts = {'device_owner': 'network:router_interface',
                   'device_id': router["id"]}
    ports = openstack.client_neutron.list_ports(**search_opts)['ports']
    for port in ports:
        log.info("Removes port {} from router", port["mac_address"])
        if not read_only:
            openstack.client_neutron.remove_interface_router(router["id"], body=dict(port_id=port['id']))
    if not read_only:
        openstack.client_neutron.delete_router(router["id"])


@ignore_exception
def delete_routers(read_only):
    all_routers = openstack.get_routers()
    routers = [router for router in all_routers if not get_tenant(router['tenant_id'])]
    for router in routers:
        delete_router(router, read_only)

    return len(routers)


@ignore_exception
def delete_networks(read_only):
    all_networks = openstack.get_networks()
    networks = [network for network in all_networks if not get_tenant(network['tenant_id'])]
    for network in networks:
        log.info('Deleted unassigned network {}, tenant {}', network["id"], network["tenant_id"])
        if not read_only:
            try:
                openstack.client_neutron.delete_network(network["id"])
            except Exception as e:
                log.warning("Can't delete network {}: {}", network, e)

    return len(networks)


@ignore_exception
def delete_subnets(read_only):
    all_subnets = openstack.get_subnets()
    subnets = [subnet for subnet in all_subnets if not get_tenant(subnet['tenant_id'])]
    for subnet in subnets:
        log.info('Deleted unassigned subnet {}, name: {}, gateway: {}, network: {}, tenant {}',
                 subnet["id"], subnet["name"], subnet["gateway_ip"], subnet["network_id"], subnet["tenant_id"])
        if not read_only:
            try:
                openstack.client_neutron.delete_subnet(subnet["id"])
            except Exception as e:
                log.warning("Can't delete subnet {}: {}", subnet, e)

    return len(subnets)


@ignore_exception
def delete_ports(read_only):
    all_ports = openstack.get_ports()
    ports = [port for port in all_ports if port['tenant_id'] and not get_tenant(port['tenant_id'])]
    for port in ports:
        log.info('Deleted unassigned port {}, ips: {}, network: {}, tenant: {}',
                 port["mac_address"], ",".join(ip["ip_address"] for ip in port["fixed_ips"]), port["network_id"], port["tenant_id"])
        if not read_only:
            try:
                openstack.client_neutron.delete_port(port['id'])
            except Exception as e:
                log.warning("Can't delete port {}: {}", port, e)

    return len(ports)


@ignore_exception
def delete_security_groups(read_only):
    all_groups = openstack.get_neutron_security_groups()
    groups = [group['id'] for group in all_groups if not get_tenant(group['tenant_id'])]
    for group in groups:
        log.info('Deleted unassigned security group {}', group)
        if not read_only:
            openstack.client_neutron.delete_security_group(group)

    return len(groups)


def delete_unassigned_resources(read_only):
    fips = delete_floatingips(read_only)
    instances = delete_instances(read_only)
    volumes = delete_volumes(read_only)
    snapshots = delete_snapshots(read_only)
    images = delete_images(read_only)
    routers = delete_routers(read_only)
    networks = delete_networks(read_only)
    subnets = delete_subnets(read_only)
    ports = delete_ports(read_only)
    sgroups = delete_security_groups(read_only)

    log.info('Deleted unassigned resources: {} floating ips, {} instances, {} volumes, {} snapshots, {} images, '
             '{} routers, {} networks, {} subnets, {} ports, {} security groups', fips, instances, volumes, snapshots,
             images, routers, networks, subnets, ports, sgroups)


def main():
    import docopt
    opt = docopt.docopt(__doc__)
    verbose = opt["--verbose"]

    with setup_backend_logbook('stderr', openstack_log_level="DEBUG" if verbose else "INFO",
                               min_level="DEBUG" if verbose else "INFO"):
        read_only = opt["--read-only"]
        if opt['--unassigned']:
            delete_unassigned_resources(read_only)
        delete_by_keyword(opt['--keyword'], read_only)


if __name__ == "__main__":
    main()
