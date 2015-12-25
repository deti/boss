import conf
import logbook
import time
import errors
from collections import namedtuple
from fitter.aggregation import constants
from fitter.aggregation.helpers import convert_to
from model import Flavor, Service, autocommit
from os_interfaces.openstack_wrapper import openstack
from kids.cache import cache


Usage = namedtuple('Usage', ['service_id', 'volume', 'resource_name', 'start', 'end'])


def get_counter_volume(sample):
    if hasattr(sample, "counter_volume"):
        return sample.counter_volume or 0
    else:
        return sample.volume or 0


def get_metadata(sample):
    return getattr(sample, "metadata", {})


def get_counter_unit(sample):
    if hasattr(sample, "counter_unit"):
        return sample.counter_unit
    else:
        return sample.unit


def get_flavor(sample):
    metadata = get_metadata(sample)
    flavor_name = metadata.get("flavor.name")
    if flavor_name:
        return flavor_name
    return metadata["instance_type"]


@autocommit
def handle_unknown_flavor(flavor_name):
    flavor = openstack.get_nova_flavor(name=flavor_name)
    service = Service.create_vm(
        {'en': 'Public Flavor %s' % flavor_name, 'ru': 'Публичный Флавор %s' % flavor_name},
        flavor_info={'flavor_id': flavor_name, 'vcpus': flavor.vcpus, 'ram': flavor.ram, 'disk': flavor.disk,
                     'network': 0},
        mutable=False
    )
    flavor_id = service.service_id

    return flavor_id


class Transformer(object):

    def __init__(self, name_field="name"):
        self.name_field = name_field

    def transform_usage(self, name, data, time_label):
        raise NotImplementedError()

    @staticmethod
    def filter_by_timelabel(data, time_label):
        start, end = time_label.datetime_range()
        return (entry for entry in data if start <= entry.timestamp < end)

    def max_volume(self, data, time_label):
        max_event = max(self.filter_by_timelabel(data, time_label), default=None, key=get_counter_volume)
        if max_event is not None:
            return get_counter_volume(max_event)
        return None

    @staticmethod
    def time_range(data, time_label):
        start, end = time_label.datetime_range()
        return max(start, data[0].timestamp), min(end, data[-1].timestamp)

    def get_name(self, data):
        if not data or not self.name_field:
            return None
        metadata = get_metadata(data[-1])
        return metadata.get(self.name_field)


class Uptime(Transformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    """

    def transform_usage(self, name, data, time_label):
        # get tracked states from config
        tracked = conf.fitter.transformers.uptime.tracked_states
        tracked_states = {constants.states[state] for state in tracked}

        used_by_flower = {}

        start, end = time_label.datetime_range()

        if not data:
            # there was no data for this period.
            return []

        previous_flavor = None
        resource_name = self.get_name(data)

        def _add_usage(flavor, ts, previous_flavor):
            min_max_ts = used_by_flower.get(flavor)

            if min_max_ts is None:
                used_by_flower[flavor] = ts, ts
            else:
                ts = min(end, max(min_max_ts[0], ts))
                used_by_flower[flavor] = min_max_ts[0], ts

            if previous_flavor:
                min_max_ts = used_by_flower[previous_flavor]
                used_by_flower[previous_flavor] = min_max_ts[0], ts

        for val in data:
            if get_counter_volume(val) in tracked_states:
                flavor_name = get_flavor(val)
                _add_usage(flavor_name, val.timestamp, previous_flavor)
                previous_flavor = flavor_name
            else:
                if previous_flavor:
                    ts = min(end, max(start, val.timestamp))
                    min_max_ts = used_by_flower[previous_flavor]
                    used_by_flower[previous_flavor] = min_max_ts[0], ts
                    previous_flavor = None

        # extend the last state we know about, to the end of the window,
        # if we saw any actual uptime.
        if get_counter_volume(data[-1]) in tracked_states and data[-1].timestamp > start:
            _add_usage(get_flavor(data[-1]), end, previous_flavor)

        # map the flavors to names on the way out
        result = []
        for flavor_name, (usage_start, usage_end) in used_by_flower.items():
            usage_start = max(start, usage_start)
            usage_end = min(end, usage_end)
            if usage_start < usage_end:
                try:
                    flavor_id = Flavor.get_service_id(flavor_name)
                except errors.FlavorNotFound:
                    logbook.error("Flavor with name {} doesn't exist in database. Created fake entry for this flavor",
                                  flavor_name)
                    flavor_id = handle_unknown_flavor(flavor_name)

                result.append(Usage(flavor_id, 1, resource_name, usage_start, usage_end))
        return result


class FromImage(Transformer):
    """
    Transformer for creating Volume entries from instance metadata.
    Checks if image was booted from image, and finds largest root
    disk size among entries.
    This relies heavily on instance metadata.
    """

    def transform_usage(self, name, data, time_label):
        from_image = conf.fitter.transformers.from_image
        checks = from_image.md_keys
        none_values = from_image.none_values
        service = from_image.service
        size_sources = from_image.size_keys
        resource_name = self.get_name(data)

        size = 0
        for entry in self.filter_by_timelabel(data, time_label):
            metadata = get_metadata(entry)
            for source in checks:
                if metadata.get(source, object()) in none_values:
                    continue

            for source in size_sources:
                try:
                    root_size = float(metadata[source])
                except (KeyError, ValueError):
                    continue
                if root_size > size:
                    size = root_size
        if size:
            return [Usage(service, size, resource_name, *self.time_range(data, time_label))]
        else:
            return []


class GaugeMax(Transformer):
    """
    Transformer for max-integration of a gauge value over time.
    If the raw unit is 'gigabytes', then the transformed unit is
    'gigabyte-hours'.
    """

    def transform_usage(self, name, data, time_label):
        max_vol = self.max_volume(data, time_label)
        if max_vol is not None:
            return [Usage(name, max_vol, self.get_name(data), *self.time_range(data, time_label))]
        else:
            return []


class StorageMax(Transformer):
    """
    Variation on the GaugeMax Transformer that checks for
    volume_type and uses that as the service, or uses the
    default service name.
    """
    UPDATE_INTERVAL = 5 * 60

    def __init__(self, name_field=None, volume_types=None):
        super().__init__(name_field)
        self.volume_types = volume_types or {}
        self.volume_types_cache = {}
        self.cache_updated_at = 0

    def get_volume_type_list(self):
        if time.time() < self.cache_updated_at + self.UPDATE_INTERVAL:
            # prevent very often updates
            return
        self.volume_types_cache = {vtype.id: vtype.name for vtype in openstack.client_cinder.volume_types.list()}
        if not self.volume_types_cache:
            logbook.error("Volume type list if empty")
        logbook.info("Got list of volume types: {}", self.volume_types_cache)
        self.cache_updated_at = time.time()

    def volume_type(self, volume_type_id):
        if not self.volume_types_cache:
            self.get_volume_type_list()

        volume_type = self.volume_types_cache.get(volume_type_id)
        if not volume_type:
            # probably this is new type, try to refresh volume list
            self.get_volume_type_list()
            volume_type = self.volume_types_cache.get(volume_type_id)

        return volume_type

    def transform_usage(self, name, data, time_label):
        max_vol = self.max_volume(data, time_label)
        if max_vol is None:
            return []

        unit = get_counter_unit(data[-1])
        max_vol = convert_to(max_vol, unit, 'B')
        resource_name = self.get_name(data)

        metadata = get_metadata(data[-1])
        service = name
        if "volume_type" in metadata:
            volume_type = self.volume_type(metadata['volume_type'])
            if volume_type:
                service = self.volume_types.get(volume_type, service)

        return [Usage(service, max_vol, resource_name, *self.time_range(data, time_label))]


class GaugeSum(Transformer):
    """
    Transformer for sum-integration of a gauge value for given period.
    """
    def transform_usage(self, name, data, time_label):
        total = sum(get_counter_volume(entry) for entry in self.filter_by_timelabel(data, time_label))
        if total:
            return [Usage(name, total, self.get_name(data), data[0].timestamp, data[-1].timestamp)]
        else:
            return []


class GaugeNetworkService(Transformer):
    """Transformer for Neutron network service, such as LBaaS, VPNaaS,
    FWaaS, etc.
    """

    STATE_ACTIVE = 1

    def transform_usage(self, name, data, time_label):
        # The network service pollster of Ceilometer is using
        # status as the volume(see https://github.com/openstack/ceilometer/
        # blob/master/ceilometer/network/services/vpnaas.py#L55), so we have
        # to check the volume to make sure only the active service is
        # charged(0=inactive, 1=active).

        active = any(get_counter_volume(entry) == self.STATE_ACTIVE
                     for entry in self.filter_by_timelabel(data, time_label))
        if active:
            return [Usage(name, active, self.get_name(data), *self.time_range(data, time_label))]
        else:
            return []

# Transformer dict for us with the config.
# All usable transformers need to be here.
_active_transformers = {
    'Uptime': Uptime,
    'StorageMax': StorageMax,
    'GaugeMax': GaugeMax,
    'GaugeSum': GaugeSum,
    'FromImage': FromImage,
    'GaugeNetworkService': GaugeNetworkService
}


@cache
def get_transformer(name, **args):
    transformer_class = _active_transformers[name]
    return transformer_class(**args)
