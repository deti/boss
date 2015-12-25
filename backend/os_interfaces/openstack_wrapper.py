import logbook as log
import random
import string
import logging
import arrow
import time
from utils import find_first
from contextlib import contextmanager

from keystoneclient.session import Session
from keystoneclient.auth.identity.v2 import Password
from ceilometerclient.openstack.common.apiclient.exceptions import ClientException
import keystoneclient.v2_0.client as ksclient
import ceilometerclient.client as cclient
import glanceclient.v2.client as glance_client
import cinderclient.v2.client as cinder_client
import novaclient.client as nvclient
import neutronclient.v2_0.client as neutron_client
from neutronclient.common.exceptions import BadRequest, Conflict, NetworkInUseClient
from keystoneclient.exceptions import NotFound, Unauthorized
from novaclient.exceptions import Conflict as NovaConflict
from utils import timed
from collections import defaultdict
from os_interfaces.helpers import get_openstack_list_paginator

import conf


class VM_STATE:
    """ from https://github.com/openstack/nova/blob/master/nova/compute/vm_states.py
    """
    ACTIVE = 'active'  # VM is running
    BUILDING = 'building'  # VM only exists in DB
    PAUSED = 'paused'
    SUSPENDED = 'suspended'  # VM is suspended to disk.
    STOPPED = 'stopped'  # VM is powered off, the disk image is still there.
    RESCUED = 'rescued'  # A rescue image is running with the original VM image
    # attached.
    RESIZED = 'resized'  # a VM with the new size is active. The user is expected
    # to manually confirm or revert.
    SOFT_DELETED = 'soft-delete'  # VM is marked as deleted but the disk images are
    # still available to restore.
    DELETED = 'deleted'  # VM is permanently deleted.
    ERROR = 'error'
    SHELVED = 'shelved'  # VM is powered off, resources still on hypervisor
    SHELVED_OFFLOADED = 'shelved_offloaded'  # VM and associated resources are not on hypervisor

    all_states = {ACTIVE, BUILDING, PAUSED, SUSPENDED, STOPPED, RESCUED, RESIZED,
                  SOFT_DELETED, DELETED, ERROR, SHELVED, SHELVED_OFFLOADED}

    @staticmethod
    def is_running(state):
        return state.lower() == VM_STATE.ACTIVE


class OpenStackAuth(object):
    __client_nova = None
    __client_glance = None
    __client_cinder = None
    __client_neutron = None
    __client_keystone = None
    __client_ceilometer = None
    __auth_session = None

    def __init__(self, openstack_conf):
        self.__auth = openstack_conf.auth
        self.request_timeout = openstack_conf.request_timeout
        self.ceilometer_timeout = openstack_conf.ceilometer_timeout
        self.connect_retries = openstack_conf.connect_retries

    @contextmanager
    def change_auth(self, users_auth):
        """Change auth to User's credentials.
        Use this to do something by user's privileges.
        """
        self.__auth = {
            'username': users_auth['username'],
            'password': users_auth['password'],
            'auth_url': users_auth.get('auth_url', conf.openstack.auth.auth_url), # Use this from conf here?
            'tenant_id': users_auth['tenant_id']
        }
        self.__client_nova = None
        self.__client_glance = None
        self.__client_cinder = None
        self.__client_neutron = None
        self.__client_keystone = None
        self.__client_ceilometer = None
        self.__auth_session = None
        log.debug("Change openstack auth to {}", users_auth["username"])
        try:
            yield
        finally:
            self.__client_nova = None
            self.__client_cinder = None
            self.__client_neutron = None
            self.__client_keystone = None
            self.__client_ceilometer = None
            self.__auth_session = None
            self.__init__(conf.openstack)

    @property
    def auth_session(self):
        if not self.__auth_session:
            log.debug("Creating auth session with args {}", {k: v for k, v in self.__auth.items() if k != 'password'})
            plugin = Password(**self.__auth)
            self.__auth_session = Session(auth=plugin, timeout=self.request_timeout)
        return self.__auth_session

    @property
    def client_ceilometer(self):
        if not self.__client_ceilometer:
            self.__client_ceilometer = cclient.get_client(version=2,
                                                          timeout=self.ceilometer_timeout,
                                                          connect_retries=self.connect_retries,
                                                          **self.__auth)
        return self.__client_ceilometer

    @property
    def client_keystone(self):
        if not self.__client_keystone:
            log.debug("Creating keystone client")
            self.__client_keystone = ksclient.Client(session=self.auth_session,
                                                     connect_retries=self.connect_retries,
                                                     timeout=self.request_timeout)
        return self.__client_keystone

    @property
    def client_nova(self):
        log_level = logging.getLevelName(conf.openstack.loglevel)
        http_log_debug = log_level == "DEBUG" or log_level == 10
        if not self.__client_nova:
            self.__client_nova = nvclient.Client(2, # version
                                                 http_log_debug=http_log_debug,
                                                 session=self.auth_session,
                                                 connect_retries=self.connect_retries,
                                                 timeout=self.request_timeout)
        return self.__client_nova

    @property
    def client_cinder(self):
        if not self.__client_cinder:
            self.__client_cinder = cinder_client.Client(session=self.auth_session,
                                                        connect_retries=self.connect_retries,
                                                        timeout=self.request_timeout)
        return self.__client_cinder

    @property
    def client_glance(self):
        if not self.__client_glance:
            self.__client_glance = glance_client.Client(session=self.auth_session)
        return self.__client_glance

    @property
    def client_neutron(self):
        if not self.__client_neutron:
            self.__client_neutron = neutron_client.Client(session=self.auth_session,
                                                          connect_retries=self.connect_retries,
                                                          timeout=self.request_timeout)
        return self.__client_neutron


class OpenStackWrapper(OpenStackAuth):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @get_openstack_list_paginator()  # pagination should be ok
    def get_tenants(self, limit=None, marker=None):
        """Returns list of available tenants"""
        tenants = self.client_keystone.tenants.list(limit=limit, marker=marker)
        return tenants

    def get_tenant(self, tenant_id):
        """Returns tenant with given tenant_id"""
        try:
            tenants = self.client_keystone.tenants.get(tenant_id)
        except NotFound as e:
            log.debug(e)
            return None

        return tenants

    def create_tenant(self, email, customer_id):
        """Create new tenant with default limits"""
        name = self.make_id(customer_id, email, "tenant")
        tenant = find_first(self.get_tenants(), lambda x: x.name == name)
        if tenant is None:
            tenant = self.client_keystone.tenants.create(tenant_name=name,
                                                         description=self.make_description(name, email),
                                                         enabled=True)
            log.info('OpenStack create tenant. email: {}, tenant_id: {}', email, tenant.id)
        else:
            log.info('Tenant for customer {} already exists. Tenant id: {}', email, tenant.id)
        return tenant

    def delete_tenant(self, tenant_id, tenant=None):
        """Delete tenant from OpenStack by tenant_id"""
        if tenant is None:
            tenant = self.client_keystone.tenants.get(tenant_id)
        res = self.client_keystone.tenants.delete(tenant_id)
        log.info('OpenStack delete tenant. Tenant name: {}, tenant_id: {}, tenant description: {}', tenant.name,
                 tenant_id, tenant.description)
        return res

    # @get_openstack_list_paginator()  # limitation is not working
    def get_users(self, limit=None, marker=None):
        """Returns list of available users"""
        return self.client_keystone.users.list(limit=limit, marker=marker)

    def get_user(self, user_id):
        """Returns user with given user_id"""
        return self.client_keystone.users.get(user_id)

    # @get_openstack_list_paginator()  # limitation is not working
    def get_networks(self, retrieve_all=True, **params):
        """Return list of networks"""
        return self.client_neutron.list_networks(retrieve_all=retrieve_all, **params)['networks']

    # @get_openstack_list_paginator()  # limitation is not working
    def get_subnets(self, retrieve_all=True, **params):
        """Return list of subnets"""
        return self.client_neutron.list_subnets(retrieve_all=retrieve_all, **params)['subnets']

    # @get_openstack_list_paginator()  # limitation is not working
    def get_routers(self, retrieve_all=True, **params):
        """Return list of routers"""
        return self.client_neutron.list_routers(retrieve_all=retrieve_all, **params)['routers']

    # @get_openstack_list_paginator()  # limitation is not working
    def get_ports(self, retrieve_all=True, **params):
        """Return list of ports"""
        return self.client_neutron.list_ports(retrieve_all=retrieve_all, **params)['ports']

    def get_auth_info(self, username, password, tenant_id=None, ):
        """Return auth information"""
        identity_info = self.client_keystone.get_raw_token_from_identity_service(conf.openstack.auth.auth_url,
                                                                                 username=username,
                                                                                 password=password,
                                                                                 tenant_id=tenant_id)
        return identity_info

    def validate_token(self, token):
        try:
            res = self.client_keystone.tokens.validate(token)
        except NotFound:
            return {}
        return res._info['token']

    def delete_ports(self, tenant_id, tenant_name=None):
        ports = self.get_ports(tenant_id=tenant_id)
        for port in ports:
            log.info('Deleting port {} of tenant {} (id: {})', port['id'], tenant_name, tenant_id)
            self.client_neutron.delete_port(port['id'])

        return len(ports)

    def get_neutron_security_groups(self, retrieve_all=True, **params):
        """Returns list of security_groups"""
        return self.client_neutron.list_security_groups(retrieve_all=retrieve_all, **params)['security_groups']

    def delete_security_groups(self, tenant_id, tenant_name=None):
        security_groups = self.get_neutron_security_groups(tenant_id=tenant_id)
        for security_group in security_groups:
            log.info('Deleting security group {} of tenant {} (id: {})', security_group['id'], tenant_name, tenant_id)
            self.client_neutron.delete_security_group(security_group['id'])

        return len(security_groups)

    def create_default_security_group_rule(self, tenant_id):
        security_group_id = self.get_neutron_security_groups(tenant_id=tenant_id)[0]['id']
        body = {'security_group_rule':
                    {'direction': 'ingress',
                     'security_group_id': security_group_id,
                     'tenant_id': tenant_id
                    }
        }
        try:
            self.client_neutron.create_security_group_rule(body=body)
        except Conflict as e:
            log.info("Can't create rule for tenant {}. Exception: {}", tenant_id, e)

    @get_openstack_list_paginator()  # pagination should be OK
    def get_volumes(self, all_tenants=True, limit=None, marker=None, **kwargs):
        """Returns list of volumes"""
        search_opts = dict(all_tenants=all_tenants, **kwargs)
        return self.client_cinder.volumes.list(search_opts=search_opts, limit=limit, marker=marker)

    def delete_volumes(self, tenant_id, tenant_name=None):
        volumes = self.get_volumes(tenant_id=tenant_id)
        for volume in volumes:
            log.info('Deleting volume {} of tenant {} (id: {})', volume.id, tenant_name, tenant_id)
            self.client_cinder.volumes.delete(volume.id)

        return len(volumes)

    # @get_openstack_list_paginator()  # limit is working, marker - not.
    def get_snapshots(self, **kwargs):
        """Returns list of snapshots"""
        search_opts = dict(all_tenants=True, **kwargs)
        return self.client_cinder.volume_snapshots.list(search_opts=search_opts)

    def delete_snapshots(self, tenant_id, tenant_name=None):
        snapshots = self.get_snapshots(tenant_id=tenant_id)
        for snapshot in snapshots:
            log.info('Deleting snapshot {} of tenant {} (id: {})', snapshot.id, tenant_name, tenant_id)
            self.client_cinder.volume_snapshots.delete(snapshot.id)

        return len(snapshots)

    # @get_openstack_list_paginator()  # limit is not working
    def get_images(self, all_tenants=True, page_size=conf.openstack.request_page_size, **kwargs):
        search_opts = dict(all_tenants=all_tenants, **kwargs)
        return self.client_glance.images.list(search_opts=search_opts, page_size=page_size)

    def delete_images(self, tenant_id, tenant_name=None):
        all_images = self.client_nova.images.list()
        images = [image.id for image in all_images if image.metadata.get('owner_id', None) == tenant_id]
        for image in images:
            log.info('Deleting image {} of tenant {} (id: {})', image, tenant_name, tenant_id)
            self.client_nova.images.delete(image)

        return len(images)

    @staticmethod
    def make_id(customer_id, email, prefix):
        iden = "%s-%08x" % (prefix, customer_id)
        if conf.devel.debug:
            iden += "%s-%s-%s" % (conf.region, conf.availability_zone, email)
        return iden[:64]

    @staticmethod
    def make_description(name, email):
        description = "%s-%s" % (name, email)
        return description

    def create_user(self, email, customer_id, tenant_id, password, enabled=True):
        name = self.make_id(customer_id, email, "user")

        user = find_first(self.get_users(), lambda x: getattr(x, "email", None) == email and
                          getattr(x, "name", None) == name)
        if user is None:
            user = self.client_keystone.users.create(name=name,
                                                     password=password,
                                                     email=email,
                                                     tenant_id=tenant_id,
                                                     enabled=enabled)
            log.info('OpenStack create user. email: {}, user_id: {}, tenant_id: {}', email, user.id, tenant_id)
        else:
            log.info('User for email {} already exists: {}', email, user.id)
            self.client_keystone.users.update_password(user, password)
            user = self.client_keystone.users.update_tenant(user, tenant_id)
        return user

    def update_user(self, user_id, **kwargs):
        res = self.client_keystone.users.update(user_id, **kwargs)
        return res

    def update_user_password(self, user_id, new_password):
        res = self.client_keystone.users.update_password(user_id, new_password)
        return res

    def delete_user(self, user_id):
        user = self.client_keystone.users.get(user_id)
        res = self.client_keystone.users.delete(user_id)
        log.info('OpenStack delete user. User name: {}, user_id: {}', user.name, user_id)
        return res

    def attach_flavors_to_tenant(self, tenant_id, tariff_flavors):
        os_flavors_ids = {flavor.name.lower(): flavor.id for flavor in self.get_nova_flavors(is_public=None)}
        for flavor in tariff_flavors:
            try:
                self.client_nova.flavor_access.add_tenant_access(os_flavors_ids[flavor.lower()], tenant_id)
                log.info('Attach flavor {} to tenant {}', flavor, tenant_id)
            except NovaConflict as e:
                log.info("Can't attach flavor {} to tenant {}. Exception: {}", flavor.lower(), tenant_id, e)

    def attached_flavors(self, tenant_id):
        os_flavors = self.get_nova_flavors(is_public=None)
        attached = {}
        for flavor in os_flavors:
            if not flavor.is_public:
                attached_tenants = self.client_nova.flavor_access.list(flavor=flavor.id)
                tenant_attached = find_first(attached_tenants, lambda x: x.tenant_id == tenant_id)
                if tenant_attached:
                    attached[flavor.name] = flavor

        return attached

    def change_flavors(self, tenant_id, tariff_flavors):
        log.info("Change flavors for tenant {}: {}", tenant_id, tariff_flavors)
        tariff_flavors = set(tariff_flavors)
        attached_flavors = self.attached_flavors(tenant_id)

        flavors_to_add = tariff_flavors - set(attached_flavors)
        flavors_to_delete = set(attached_flavors) - tariff_flavors

        self.attach_flavors_to_tenant(tenant_id, flavors_to_add)

        for flavor in flavors_to_delete:
            self.client_nova.flavor_access.remove_tenant_access(attached_flavors[flavor].id, tenant_id)
            log.info('Detach flavor {} from tenant {}', flavor, tenant_id)

    def create_tenant_and_user(self, email, customer_id, flavors, password=None, enabled=True):
        tenant = self.create_tenant(email, customer_id)
        net = self.create_default_network('DefaultPrivateNet', tenant.id)
        subnet = self.create_default_subnet(net['id'], tenant.id, conf.openstack.dns_nameservers)
        router = self.create_default_router(tenant.id, conf.openstack.external_net)
        self.create_default_security_group_rule(tenant.id)
        self.attach_subnet_to_router(router['id'], subnet['id'])
        if password is None:
            password = self.generate_password()
        user = self.create_user(email, customer_id, tenant.id, password=password, enabled=enabled)
        self.set_default_quotas(tenant.id)
        self.change_flavors(tenant.id, flavors)
        self.set_default_user_role(user, tenant)
        res = {
            'username': user.username,
            'password': password,
            'name': user.name,
            'email': user.email,
            'enabled': user.enabled,
            'tenant_id': user.tenantId,
            'user_id': user.id,
            'tenant_name': tenant.name
        }
        return res

    def reset_user_password(self, user_id):
        password = self.generate_password()
        self.update_user_password(user_id, password)

        return password

    def delete_tenant_and_user(self, user_id, tenant_id, tenant=None):
        deleted = {}
        if user_id:
            self.delete_user(user_id=user_id)
            deleted['users'] = 1
        if tenant_id:
            self.delete_tenant(tenant_id=tenant_id, tenant=tenant)
            deleted['tenants'] = 1

        return deleted

    def final_delete(self, user_id, tenant_id):
        deleted = {}
        if tenant_id:
            tenant = self.client_keystone.tenants.get(tenant_id)
            deleted.update(self.delete_resources(tenant_id, tenant.name))
            deleted.update(self.delete_tenant_and_user(user_id, tenant_id, tenant))

        return deleted

    def delete_resources(self, tenant_id, tenant_name=None):
        deleted = dict(
            floatingips=self.delete_floating_ips(tenant_id, tenant_name),
            instances=self.delete_instances(tenant_id, tenant_name),
            volumes=self.delete_volumes(tenant_id, tenant_name),
            snapshots=self.delete_snapshots(tenant_id, tenant_name),
            images=self.delete_images(tenant_id, tenant_name),
            vpns=self.delete_vpns(tenant_id, tenant_name),
            routers=self.delete_routers(tenant_id, tenant_name),
            networks=self.delete_networks(tenant_id, tenant_name),
            subnets=self.delete_subnets(tenant_id, tenant_name),
            ports=self.delete_ports(tenant_id, tenant_name),
            security_groups=self.delete_security_groups(tenant_id, tenant_name),
        )
        return deleted

    def create_network(self, name, tenant_id):
        network_body = {'network': {
            'name': name,
            'admin_state_up': True,
            'tenant_id': tenant_id
        }}
        network = self.client_neutron.create_network(body=network_body)['network']
        log.info('Openstack create network. Name: {}, Id: {}', network['name'], network['id'])
        return network

    def delete_networks(self, tenant_id, tenant_name=None):
        networks = self.get_networks(tenant_id=tenant_id)
        for network in networks:
            ports = self.get_ports(network_id=network['id'])
            owners = [port['device_owner'] for port in ports]
            if any([owner != 'network:dhcp' for owner in owners]):
                log.warning('Network {} of tenant {} has port with owner that is not "dhcp". List of owners: {}',
                            network['id'], tenant_id, owners)
                raise NetworkInUseClient('Unable to complete operation on network %s. '
                                         'There are one or more ports still in use on the network.' % network['id'])
            else:
                try:
                    log.info('Deleting network {} of tenant {} (id: {})', network['id'], tenant_name, tenant_id)
                    self.client_neutron.delete_network(network['id'])
                except NetworkInUseClient as e:
                    log.error("{}. List of ports' owners: {}", e, owners)
        return len(networks)

    def create_default_network(self, name, tenant_id):
        network = self.get_networks(name=name, tenant_id=tenant_id)
        if not network:
            network = self.create_network(name, tenant_id)
        else:
            log.info('Default network {} for tenant {} already exists', name, tenant_id)
            network = network[0]
        return network

    def create_subnet(self, network_id, tenant_id, dns_nameservers):
        subnet_body = {'subnet': {
            'network_id': network_id,
            'tenant_id': tenant_id,
            'cidr': '10.0.0.1/24',
            'ip_version': 4,
            'dns_nameservers': dns_nameservers
        }}
        subnet = self.client_neutron.create_subnet(body=subnet_body)['subnet']
        log.info('Openstack create subnet. Id: {}', subnet['id'])
        return subnet

    def delete_subnets(self, tenant_id, tenant_name=None):
        subnets = self.get_subnets(tenant_id=tenant_id)
        for subnet in subnets:
            log.info('Deleting subnet {} of tenant {} (id: {})', subnet['id'], tenant_name, tenant_id)
            self.client_neutron.delete_subnet(subnet['id'])

        return len(subnets)

    def create_default_subnet(self, network_id, tenant_id, dns_nameservers):
        subnet = self.get_subnets(network_id=network_id, tenant_id=tenant_id)
        if not subnet:
            subnet = self.create_subnet(network_id, tenant_id, dns_nameservers)
        else:
            log.info('Default subnet for tenant {}, network {} already exists', tenant_id, network_id)
            subnet = subnet[0]
        return subnet

    def create_router(self, tenant_id, external_network=None):
        router_body = {'router': {'tenant_id': tenant_id}}
        if external_network:
            router_body['router']['external_gateway_info'] = {
                'network_id': external_network
            }

        router = self.client_neutron.create_router(body=router_body)['router']
        log.info('Openstack create router. Id: {}', router['id'])
        return router

    def delete_routers(self, tenant_id, tenant_name=None):
        routers = self.get_routers(tenant_id=tenant_id)
        for router in routers:
            search_opts = {'device_owner': 'network:router_interface',
                           'device_id': router['id']}
            ports = self.get_ports(**search_opts)
            for port in ports:
                self.client_neutron.remove_interface_router(router['id'], body=dict(port_id=port['id']))
            log.info('Deleting router {} of tenant {} (id: {})', router['id'], tenant_name, tenant_id)
            self.client_neutron.delete_router(router['id'])

        return len(routers)

    def create_default_router(self, tenant_id, external_network=None):
        router = self.get_routers(tenant_id=tenant_id)
        if not router:
            router = self.create_router(tenant_id, external_network)
        else:
            log.info('Default router for tenant {} already exists', tenant_id)
            router = router[0]
        return router

    def attach_subnet_to_router(self, router_id, subnet_id):
        body = {
            'subnet_id': subnet_id
        }
        try:
            self.client_neutron.add_interface_router(router_id, body=body)
            log.info('Openstack attach subnet {} to router {}', subnet_id, router_id)
        except BadRequest as e:
            log.info('Subnet {} is already attached to router {}. Exception: {}', subnet_id, router_id, e)

    def generate_password(self):
        """Generates new password for OS user account"""
        password_length = random.randint(8, 16)
        password_chars = string.ascii_letters + string.digits + '@#$%&*()'
        return ''.join([random.choice(password_chars) for _ in range(password_length)])

    def set_default_quotas(self, tenant_id):
        self.change_tenant_quotas(tenant_id=tenant_id, **conf.template.test_customer)

    def get_quotas(self, tenant_id, user_id=None):
        res = {}
        nova_quotas = self.client_nova.quotas.get(tenant_id, user_id=user_id)
        cinder_quotas = self.client_cinder.quotas.get(tenant_id)
        neutron_quotas = self.client_neutron.show_quota(tenant_id)

        res.update({
            'instances': nova_quotas.instances,
            'cores': nova_quotas.cores,
            'ram': nova_quotas.ram,
            'floating_ips': nova_quotas.floating_ips,
            'fixed_ips': nova_quotas.fixed_ips,
            'metadata_items': nova_quotas.metadata_items,
            'injected_files': nova_quotas.injected_files,
            'injected_file_content_bytes': nova_quotas.injected_file_content_bytes,
            'injected_file_path_bytes': nova_quotas.injected_file_path_bytes,
            'key_pairs': nova_quotas.key_pairs,
            'security_groups': nova_quotas.security_groups,
            'security_group_rules': nova_quotas.security_group_rules
        })
        res.update({
            'gigabytes': cinder_quotas.gigabytes,
            'snapshots': cinder_quotas.snapshots,
            'volumes': cinder_quotas.volumes,
        })
        res.update({
            'floatingip': neutron_quotas.floatingip,
            'network': neutron_quotas.network,
            'port': neutron_quotas.port,
            'router': neutron_quotas.router,
            'subnet': neutron_quotas.subnet,
        })
        return res

    def get_floating_ips(self, tenant_id):
        ips = self.client_neutron.list_floatingips(tenant_id=tenant_id)['floatingips']
        return ips

    def delete_floating_ip(self, ip_id):
        self.client_neutron.delete_floatingip(ip_id)

    def delete_floating_ips(self, tenant_id, tenant_name=None):
        ips = self.get_floating_ips(tenant_id)
        for ip in ips:
            log.info("Deleting of floating ip '{}' of tenant '{}' (id: {})", ip['floating_ip_address'], tenant_name,
                     tenant_id)
            self.delete_floating_ip(ip['id'])

        return len(ips)

    def get_vpns(self, tenant_id):
        vpns = self.client_neutron.list_vpnservices(tenant_id=tenant_id)['vpnservices']
        return vpns

    def delete_vpns(self, tenant_id, tenant_name=None):
        vpns = self.get_vpns(tenant_id)
        for vpn in vpns:
            self.client_neutron.delete_vpnservice(vpn['id'])
            log.info("Deleting vpn {} of tenant {} (id: {})", vpn['id'], tenant_name, tenant_id)

        return len(vpns)

    def get_nova_limits(self, tenant_id):
        return self.client_nova.limits.get(tenant_id=tenant_id)._info.get('absolute', {})

    def get_limits(self, tenant_id, username, password):
        nova_limits = self.get_nova_limits(tenant_id)

        cinder_limits = defaultdict(lambda: None)
        if username and password:
            try:
                user_auth = dict(username=username, password=password, tenant_id=tenant_id)
                with self.change_auth(user_auth):
                    cinder_limits = self.client_cinder.limits.get()._info['absolute']
            except Unauthorized as e:
                log.warning("Can't get cinder limits for tenant {} and user: {} : {}",
                            tenant_id, username, e)

        res = {
            'gigabytes': cinder_limits['totalGigabytesUsed'],
            'snapshots': cinder_limits['totalSnapshotsUsed'],
            'volumes': cinder_limits['totalVolumesUsed'],
            'instances': nova_limits['totalInstancesUsed'],
            'cores': nova_limits['totalCoresUsed'],
            'ram': nova_limits['totalRAMUsed'],
            'server_groups': nova_limits['totalServerGroupsUsed'],
            'floatingip': len(self.get_floating_ips(tenant_id)),
            'port': len(self.get_ports(tenant_id=tenant_id))
        }
        return res

    def change_tenant_quotas(self, tenant_id, **quotas):
        nova_quotas = {}
        cinder_quotas = {}
        neutron_quotas = {}
        for key in conf.quotas.nova:
            value = quotas.get(key)
            if value is not None:
                nova_quotas[key] = value

        for key in conf.quotas.neutron:
            value = quotas.get(key)
            if value is not None:
                neutron_quotas[key] = value

        for key in conf.quotas.cinder:
            value = quotas.get(key)
            if value is not None:
                cinder_quotas[key] = value

        self.client_nova.quotas.update(tenant_id=tenant_id, **nova_quotas)
        self.client_cinder.quotas.update(tenant_id=tenant_id, **cinder_quotas)
        self.client_neutron.update_quota(tenant_id, body={'quota': neutron_quotas})

    def get_security_groups(self, name=None):
        if name is not None:
            return self.client_nova.security_groups.find()
        return self.client_nova.security_groups.list()

    @get_openstack_list_paginator()  # ok
    def get_nova_images(self, name=None, limit=None, marker=None):
        if name is not None:
            return self.client_nova.images.find(name=name, limit=limit, marker=marker)
        return self.client_nova.images.list(limit=limit, marker=marker)

    @get_openstack_list_paginator()  # ok
    def get_nova_flavors(self, is_public=True, limit=None, marker=None):
        return self.client_nova.flavors.list(is_public=is_public, limit=limit, marker=marker)

    def get_nova_flavor(self, name):
        return self.client_nova.flavors.find(name=name, is_public=None)

    def create_flavor(self, name, ram, vcpus, disk, flavorid="auto", ephemeral=0, swap=0,
                      rxtx_factor=1.0, is_public=True):
        return self.client_nova.flavors.create(name, ram, vcpus, disk, flavorid,
                                               ephemeral, swap, rxtx_factor, is_public)

    def delete_flavor(self, name):
        flavor = self.client_nova.flavors.find(name=name)
        self.client_nova.flavors.delete(flavor.id)

    # @get_openstack_list_paginator()  # NO limit, marker or page_size available
    def get_nova_networks(self, name=None):
        if name is not None:
            return self.client_nova.networks.find(name=name)
        return self.client_nova.networks.list()

    @get_openstack_list_paginator()  # pagination should be ok
    def get_nova_servers(self, **kwargs):
        search_opts = dict(all_tenants=True, **kwargs)
        return self.client_nova.servers.list(search_opts=search_opts)

    def create_instance(self, name, image_id, flavor_id, network_id=None, keypair_name=None):
        self.client_nova.servers.create(name=name,
                                        image=image_id,
                                        flavor=flavor_id,
                                        network=network_id,
                                        key_name=keypair_name)

    def stop_instance(self, server, tenant):
        server_name = server.name
        server_id = server.id
        tenant_id = tenant.id
        tenant_name = tenant.name

        start = arrow.utcnow()

        while (arrow.utcnow() - start).seconds < conf.openstack.server_state.limit:
            server = self.client_nova.servers.get(server_id)

            task_state = server._info['OS-EXT-STS:task_state']
            server_state = server._info['OS-EXT-STS:vm_state']

            log.debug("instance '{}' (id: {}) of tenant '{}' (id: {}) is in {} vm_state and in {} task_state",
                      server_name, server_id, tenant_name, tenant_id, server_state, task_state)

            if task_state is None:
                if VM_STATE.is_running(server_state):
                    break
                elif server_state == VM_STATE.PAUSED:
                    self.client_nova.servers.unpause(server_id)
                    log.info("Unpausing instance '{}' (id: {}) of tenant '{}' (id: {}) before stopping it", server_name,
                             server_id, tenant_name, tenant_id)
                elif server_state == VM_STATE.SUSPENDED:
                    self.client_nova.servers.resume(server_id)
                    log.info("Resuming instance '{}' (id: {}) of tenant '{}' (id: {}) before stopping it", server_name,
                             server_id, tenant_name, tenant_id)
                elif server_state == VM_STATE.RESCUED:
                    self.client_nova.servers.unrescue(server_id)
                    log.info("Unrescuing instance '{}' (id: {}) of tenant '{}' (id: {}) before stopping it",
                             server_name, server_id, tenant_name, tenant_id)
                elif server_state == VM_STATE.RESIZED:
                    self.client_nova.servers.confirm_resize(server_id)
                    log.info("Confirming resized instance '{}' (id: {}) of tenant '{}' (id: {}) before stopping it",
                             server_name, server_id, tenant_name, tenant_id)
                elif server_state in \
                        (VM_STATE.STOPPED, VM_STATE.SHELVED, VM_STATE.SHELVED_OFFLOADED, VM_STATE.SOFT_DELETED,
                         VM_STATE.DELETED, VM_STATE.ERROR):
                    log.info("instance '{}' (id: {}) of tenant '{}' (id: {}) is in the '{}' state and won't be stopped",
                             server_name, server_id, tenant_name, tenant_id, server_state)
                    return

            else:
                log.info("Waiting until instance '{}' (id: {}) of tenant '{}' (id: {}) gets to the active state",
                         server_name, server_id, tenant_name, tenant_id)
                time.sleep(conf.openstack.server_state.check)

        else:
            log.error("Time limit for getting instance '{}' (id: {}) of tenant '{}' (id: {}) to the active state " \
                      "exceeded", server_name, server_id, tenant_name, tenant_id)
            return

        log.info("Stopping instance '{}' (id: {}) of tenant '{}' (id: {})", server_name, server_id, tenant_name,
                 tenant_id)

        self.client_nova.servers.stop(server_id)

    def stop_instances(self, tenant_id):
        servers = self.get_nova_servers(tenant_id=tenant_id)
        tenant = self.get_tenant(tenant_id)
        for server in servers:
            self.stop_instance(server, tenant)

    def start_instances(self, tenant_id):
        servers = self.get_nova_servers(tenant_id=tenant_id)
        for server in servers:
            self.client_nova.servers.start(server.id)
            log.info('Starting instance {} of tenant {}', server.id, tenant_id)

    def delete_instances(self, tenant_id, tenant_name=None):
        servers = self.get_nova_servers(tenant_id=tenant_id)
        for server in servers:
            log.info('Deleting instance {} of tenant {} (id: {})', server.id, tenant_name, tenant_id)
            self.client_nova.servers.delete(server.id)

        return len(servers)

    def get_tenant_usage(self, tenant_id, meter_name, start, end, limit=None):
        """ Queries ceilometer for all the entries in a given range,
           for a given meter, from this tenant."""

        query = [self.filter('timestamp', 'ge', start), self.filter('timestamp', 'lt', end)]

        if tenant_id:
            query.append(self.filter('project_id', 'eq', tenant_id))

        if meter_name:
            query.append(self.filter('meter', 'eq', meter_name))

        with timed('fetch global usage for meter %s' % meter_name):
            result = openstack.client_ceilometer.new_samples.list(q=query, limit=limit)
            log.debug("Get usage for tenant: {} and meter_name {} ({} - {}). Number records: {}",
                      tenant_id, meter_name, start, end, len(result))
            return result

    def create_user_role(self, role_name):
        role = self.client_keystone.roles.create(role_name)
        return role

    def get_role(self, role_name):
        try:
            role = self.client_keystone.roles.find(name=role_name)
        except NotFound:
            return None
        return role

    def check_user_role(self, user, role_name, tenant):
        user_roles = self.client_keystone.users.list_roles(user, tenant)
        for role in user_roles:
            if role.name == role_name:
                return role
        return None

    def set_default_user_role(self, user, tenant):
        role_name = conf.openstack.default_user_role
        role = self.check_user_role(user, role_name, tenant)
        if role:
            log.info("Role {} already assigned for user {}", role_name, user)
            return role
        role = self.get_role(role_name)
        if not role:
            log.info("Create role: {}", role_name)
            role = self.create_user_role(role_name)
        res = self.client_keystone.roles.add_user_role(user, role, tenant)
        return res

    def get_ceilometer_samples(self, q, limit):
        """ Queries ceilometer for all the entries"""
        try:
            result = openstack.client_ceilometer.new_samples.list(q=q, limit=limit)
            log.debug("[get_ceilometer_samples] query:{}, limit: {}. Number records: {}",
                      q, limit, len(result))
            return result
        except ClientException as e:
            log.error("[get_ceilometer_samples] Can't fetch usage info for query: {}, limit: {}. Error: {}",
                      q, limit, e)
            raise

    @staticmethod
    def filter(field, op, value):
        return {'field': field, 'op': op, 'value': value}

    def check_openstack_availability(self):
        self.client_keystone.tenants.list(limit=10)
        self.client_keystone.users.list(limit=10)


openstack = OpenStackWrapper(conf.openstack)
