from keystoneclient.access import AccessInfoV2
from keystoneclient.auth.identity import BaseIdentityPlugin
from keystoneclient.auth.identity.access import AccessInfoPlugin
from keystoneclient.auth.identity.v2 import Password
from keystoneclient.session import Session
import keystoneclient.v2_0.client as keystone_sclient
import ceilometerclient.v2.client as ceilometer_client
import cinderclient.v2.client as cinder_client
import novaclient.v2.client as nova_client
import neutronclient.v2_0.client as neutron_client


class OpenstackClientBase:
    _keystone_client = None
    _ceilometer_client = None
    _cinder_client = None
    _nova_client = None
    _neutron_client = None

    def __init__(self, session:Session):
        self._session = session

    @classmethod
    def init_by_plugin(cls, plugin:BaseIdentityPlugin) -> 'OpenstackClientBase':
        return cls(Session(auth=plugin))

    @classmethod
    def init_by_creds(cls, tenant_id, os_username, os_password, auth_url) -> 'OpenstackClientBase':
        plugin = Password(auth_url=auth_url, username=os_username, password=os_password, tenant_id=tenant_id)
        return cls.init_by_plugin(plugin)

    @classmethod
    def init_by_token(cls, token) -> 'OpenstackClientBase':
        plugin = AccessInfoPlugin(auth_ref=AccessInfoV2(**token))
        return cls.init_by_plugin(plugin)

    @property
    def keystone_client(self) -> keystone_sclient.Client:
        if not self._keystone_client:
            self._keystone_client = keystone_sclient.Client(session=self._session)
        return self._keystone_client

    @property
    def ceilometer_client(self) -> ceilometer_client.Client:
        if not self._ceilometer_client:
            self._ceilometer_client = ceilometer_client.Client(session=self._session)
        return self._ceilometer_client

    @property
    def cinder_client(self) -> cinder_client.Client:
        if not self._cinder_client:
            self._cinder_client = cinder_client.Client(session=self._session)
        return self._cinder_client

    @property
    def nova_client(self) -> nova_client.Client:
        if not self._nova_client:
            self._nova_client = nova_client.Client(session=self._session)
        return self._nova_client

    @property
    def neutron_client(self) -> neutron_client.Client:
        if not self._neutron_client:
            self._neutron_client = neutron_client.Client(session=self._session)
        return self._neutron_client


class OpenstackClient(OpenstackClientBase):
    def network_create(self, **kwargs):
        data = {'network': kwargs}
        return self.neutron_client.create_network(body=data)

    def network_list(self, **kwargs):
        return self.neutron_client.list_networks(**kwargs)

    def network_delete(self, network_id):
        return self.neutron_client.delete_network(network_id)

    def server_create(self, name, image, flavor, **kwargs):
        return self.nova_client.servers.create(name=name, image=image, flavor=flavor, **kwargs)

    def flavor_list(self, **kwargs):
        return self.nova_client.flavors.list(**kwargs)

    def image_list(self, **kwargs):
        return self.nova_client.images.list(**kwargs)