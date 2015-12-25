from novaclient.v2 import client as nova_client
import neutronclient.v2_0.client as neutron_client


class OpenstackClient:
    __nova_client = None
    __neutron_client = None

    def __init__(self, username:str, api_key:str, auth_url:str, tenant_id:str):
        self._auth_conf = {'username': username, 'api_key': api_key, 'auth_url': auth_url.strip(), 'tenant_id': tenant_id}

    @property
    def nova_client(self) -> nova_client.Client:
        if not self.__nova_client:
            self.__nova_client = nova_client.Client(**self._auth_conf)
        return self.__nova_client

    @property
    def neutron_client(self) -> neutron_client.Client:
        if not self.__neutron_client:
            conf = self._auth_conf.copy()
            conf['password'] = conf.pop('api_key')
            self.__neutron_client = neutron_client.Client(**conf)
        return self.__neutron_client

    def list_image(self, **kwargs):
        return self.nova_client.images.list(**kwargs)

    def list_flavor(self, **kwargs):
        return self.nova_client.flavors.list(**kwargs)

    def list_network(self, **kwargs):
        return self.neutron_client.list_networks(**kwargs)

    def create_server(self, name, image, flavor, **kwargs):
        return self.nova_client.servers.create(name, image, flavor, **kwargs)