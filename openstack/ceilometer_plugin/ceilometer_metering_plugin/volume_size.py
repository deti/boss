from oslo_log import log
from oslo_utils import timeutils
from oslo_config import cfg

from ceilometer.agent import plugin_base
from ceilometer import sample
from cinderclient.v2.client import Client as cinderclient

cfg.CONF.import_group('service_credentials', 'ceilometer.service')
cfg.CONF.import_opt('http_timeout', 'ceilometer.service')

LOG = log.getLogger(__name__)


class FitterVolumeSizePollster(plugin_base.PollsterBase):

    def get_client(self):
        return cinderclient(username=cfg.CONF.service_credentials.os_username,
                            api_key=cfg.CONF.service_credentials.os_password,
                            project_id=cfg.CONF.service_credentials.os_tenant_name,
                            auth_url=cfg.CONF.service_credentials.os_auth_url,
                            tenant_id=cfg.CONF.service_credentials.os_tenant_id,
                            cacert=cfg.CONF.service_credentials.os_cacert,
                            region_name=cfg.CONF.service_credentials.os_region_name,
                            insecure=cfg.CONF.service_credentials.insecure,
                            timeout=cfg.CONF.http_timeout)

    def get_volumes(self):
        search_opts = dict(all_tenants=True)
        client = self.get_client()
        volumes = client.volumes.list(search_opts=search_opts)
        return volumes

    @property
    def default_discovery(self):
        return 'tenant'

    def get_samples(self, manager, cache, resources):
        for tenant in resources:
            for volume in self.get_volumes():
                volume_tenant_id = getattr(volume, 'os-vol-tenant-attr:tenant_id')
                if volume_tenant_id != tenant.id:
                    continue
                yield sample.Sample(
                    name='volume.size',
                    type=sample.TYPE_GAUGE,
                    unit='GB',
                    volume=volume.size,
                    user_id=None,  # endpoint.user_id,
                    project_id=volume_tenant_id,
                    resource_id=volume.id,
                    timestamp=timeutils.utcnow().isoformat(),
                    resource_metadata={
                        'availability_zone': volume.availability_zone
                    })
