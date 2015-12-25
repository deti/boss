from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from ceilometer.agent import plugin_base
from ceilometer import neutron_client
from ceilometer import sample


LOG = log.getLogger(__name__)

class FitterFloatingIPPollster(plugin_base.PollsterBase):

    def _get_floating_ips(self):
        return self.neutron.list_floatingips()['floatingips']

    def _iter_floating_ips(self, cache, endpoint):
        key = '%s-floating_ips' % endpoint
        if key not in cache:
            cache[key] = list(self._get_floating_ips())
        return iter(cache[key])

    @property
    def default_discovery(self):
        return 'endpoint:%s' % cfg.CONF.service_types.nova

    def get_samples(self, manager, cache, resources):
        self.neutron = neutron_client.Client().client
        for endpoint in resources:
            for ip in self._iter_floating_ips(cache, endpoint):
                yield sample.Sample(
                    name='ip.floating',
                    type=sample.TYPE_GAUGE,
                    unit='ip',
                    volume=1,
                    user_id=None,  # endpoint.user_id,
                    project_id=ip['tenant_id'],
                    resource_id=ip['id'],
                    timestamp=timeutils.utcnow().isoformat(),
                    resource_metadata={
                        'address': ip['floating_ip_address']
                    })
