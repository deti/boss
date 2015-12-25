import datetime
import time
import mock

# from ceilometerclient.v2.samples import OldSample
from ceilometerclient.v2.samples import Sample
from collections import defaultdict
from operator import attrgetter
from decimal import Decimal

from model import Tenant as TenantDb, db, Customer, Tariff
from fitter.aggregation.collector import Collector
from tests.base import BaseTestCaseDB
import logbook as log


KB = 1024*1024*1024*1024
MB = KB*1024
GB = MB*1024
TB = GB*1024


class TestException(BaseException):
    pass


class Flavors:
    tiny = "m1.tiny"
    small = "m1.small"
    medium = "m1.medium"
    large = "m1.large"
    xlarge = "m1.xlarge"


class Service:
    counter_name = None
    counter_type = None
    counter_unit = None
    source = "openstack"
    default_timestamp_delta = 10 * 60

    def __init__(self, project, name, resource_id=None):
        self.project = project
        self.name = name
        self.resource_id = resource_id or self.uuid_hash(name)
        self.volume = None

    @staticmethod
    def uuid_hash(value):
        hashed = "%016x" % abs(hash(value))
        values = (hashed[:8], hashed[8:12], hashed[12:16], hashed[:4], hashed[4:])
        return "-".join(values)

    @staticmethod
    def hash(value, size=16):
        hashed = "%016x" % abs(hash(value))
        return hashed[:size]

    @staticmethod
    def format_datetime(timestamp, microseconds=False):
        if timestamp is None:
            return 'None'
        fmt = "%Y-%m-%dT%H:%M:%S"
        format_ms = "%Y-%m-%dT%H:%M:%S.%f"
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.datetime.fromtimestamp(timestamp)
        return timestamp.strftime(format_ms if microseconds else fmt)

    def make_message(self, timestamp, user_id=None):
        assert self.counter_name and self.counter_type
        message = {
            "counter_name": self.counter_name,
            "counter_type": self.counter_type,
            "counter_volume": float(self.volume),
            "counter_unit": self.counter_unit,

            "message_id": self.uuid_hash(time.time()),
            "project_id": self.project.project_id,
            "recorded_at": self.format_datetime(timestamp, microseconds=True),
            "resource_id": self.resource_id,
            "metadata": self.metadata(),
            "source": self.source,
            "user_id": user_id,
            "timestamp": self.format_datetime(timestamp)
        }
        self.project.send_message(message)
        return message

    def repeat_message(self, start, end, delta=None, user_id=None):
        delta = delta or self.default_timestamp_delta
        while start < end:
            self.make_message(start, user_id)
            if isinstance(start, int):
                start += delta
            else:
                start += datetime.timedelta(seconds=delta)

    def metadata(self):
        raise NotImplemented()


class Instance(Service):
    counter_name = "instance"
    counter_type = "gauge"
    counter_unit = "instance"

    def __init__(self, project, name, flavor_name, resource_id=None):
        super().__init__(project, name, resource_id)
        self.volume = 1.0
        self.flavor_name = flavor_name

    def metadata(self):
        metadata = {
            'OS-EXT-AZ.availability_zone': 'nova',
            'disk_gb': '20',
            'display_name': self.name,
            'ephemeral_gb': '0',
            'flavor.disk': '20',
            'flavor.ephemeral': '0',
            'flavor.id': '98b624b7-f2db-441c-92b4-ed431fac988c',
            'flavor.links': '["{u\'href\': '
                           "u'http://xxx/e447d7ad1277f20fa8e997c1/flavors/98b624b7-f2db-441c-92b4-ed431fac988c', "
                           'u\'rel\': u\'bookmark\'}"]',
            'flavor.name': self.flavor_name,
            'flavor.ram': '4096',
            'flavor.vcpus': '2',
            'host': '45275775e66fc418d3880a633009c3d38e1ce1c47af658a931861b76',
            'image.id': 'fb6b9c66-ab17-4ecf-8ce2-aa8df2878cb5',
            'image.links': '["{u\'href\': '
                          "u'http://xxx/e447d7ad129f20fa8e997c1/images/fb6b9c66-ab17-4ecf-8ce2-aa8df2878cb5', "
                          'u\'rel\': u\'bookmark\'}"]',
            'image.name': 'CentOS7_cloud',
            'image_ref': 'fb6b9c66-ab17-4ecf-8ce2-aa8df2878cb5',
            'image_ref_url': 'http://xxx/e447d7ad1277f20fa8e997c1/images/fb6b9c66-ab17-4ecf-8ce2-aa8df2878cb5',
            'instance_type': '98b624b7-f2db-441c-92b4-ed431fac988c',
            'kernel_id': 'None',
            'memory_mb': '4096',
            'name': "instance-%s" % self.hash(self.name, 4),
            'ramdisk_id': 'None',
            'root_gb': '20',
            'vcpus': '2'}
        return metadata


class Disk(Service):
    counter_name = "image.size"
    counter_type = "gauge"
    counter_unit = "B"

    def __init__(self, project, name, created_at, size, resource_id=None):
        super().__init__(project, name, resource_id)
        self.created_at = created_at
        self.deleted = False
        self.deleted_at = None
        self.updated_at = created_at
        self.volume = size

    def metadata(self):
        metadata = {
            'checksum': self.hash(self.resource_id),
            'container_format': 'bare',
            'created_at': self.format_datetime(self.created_at),
            'deleted': str(self.deleted),
            'deleted_at': self.format_datetime(self.deleted_at),
            'disk_format': 'qcow2',
            'is_public': 'False',
            'min_disk': '20',
            'min_ram': '3072',
            'name': self.name,
            'properties.base_image_ref': '28c1e3b3-b7bf-411e-91b8-ca0c07613dda',
            'properties.clean_attempts': '8',
            'properties.description': 'All-in-one OpenStack \n (Juno)',
            'properties.image_location': 'snapshot',
            'properties.image_state': 'available',
            'properties.image_type': 'snapshot',
            'properties.instance_type_ephemeral_gb': '0',
            'properties.instance_type_flavorid': '5208d690-a870-487c-be81-dfd411784df6',
            'properties.instance_type_id': '38',
            'properties.instance_type_memory_mb': '3072',
            'properties.instance_type_name': 'm1.small',
            'properties.instance_type_root_gb': '20',
            'properties.instance_type_rxtx_factor': '1.0',
            'properties.instance_type_swap': '1024',
            'properties.instance_type_vcpus': '1',
            'properties.instance_uuid': 'e03d6c5c-d675-4151-a4bd-32fe775e485d',
            'properties.kernel_id': 'None',
            'properties.network_allocated': 'True',
            'properties.owner_id': 'b5ceb8f61821433aa5cfed1f2687fe3e',
            'properties.ramdisk_id': 'None',
            'properties.user_id': '2b980628f9d644dc8870f57423e1dffa',
            'protected': 'False',
            'size': str(self.volume),
            'status': 'active',
            'updated_at': self.format_datetime(self.updated_at)}
        return metadata


class Volume(Service):
    counter_name = "volume.size"
    counter_type = "guage"
    counter_unit = "GB"

    def __init__(self, project, name, created_at, size, resource_id=None):
        super().__init__(project, name, resource_id)
        self.volume = size
        self.created_at = created_at
        self.status = "creating"

    def metadata(self):
        metadata = {
            'availability_zone': 'nova',
            'created_at': self.format_datetime(self.created_at),
            'display_name': self.name,
            'event_type': 'volume.create.start',
            'host': 'volume.controller2',
            'launched_at': '',
            'size': str(self.volume),
            'snapshot_id': 'None',
            'status': self.status,
            'tenant_id': self.project.project_id,
            'user_id': 'b01aa55a85ab41c8b3d84afc5e9a8477',
            'volume_id': self.resource_id,
            'volume_type': 'ebb29578-fbf9-47e0-92ee-1766679b41e0'}
        return metadata


class Tenant:
    def __init__(self, name, start_time):
        self.project_id = Service.hash(time.time())
        self.messages = defaultdict(list)
        self.name = name
        self.description = name
        self.event = None
        self.timestamps = None

        self.customer_email = "%s@example.com" % self.name
        self.customer_password = self.name + self.name
        self.customer = Customer.new_customer(self.customer_email, self.customer_password, None)
        self.customer_id = self.customer.customer_id
        self.customer.email_confirmed = True
        self.start_balance = Decimal(100)
        self.customer.modify_balance(self.start_balance, self.customer.tariff.currency, None, "Initial balance")
        tenant = TenantDb.create(self.project_id, name, start_time)
        self.customer.os_tenant_id = tenant.tenant_id
        db.session.add(tenant)
        db.session.commit()

    def add_disk(self, *args, **kwargs):
        return Disk(self, *args, **kwargs)

    def send_message(self, message):
        self.messages[message["counter_name"]].append(message)

    @property
    def id(self):
        return self.project_id

    @staticmethod
    def parse_timestamp(timestamp):
        date_format = "%Y-%m-%dT%H:%M:%S"
        other_date_format = "%Y-%m-%dT%H:%M:%S.%f"

        try:
            return datetime.datetime.strptime(timestamp, date_format)
        except ValueError:
            return datetime.datetime.strptime(timestamp, other_date_format)

    def prepare_messages(self):
        self.event = defaultdict(list)
        self.timestamps = defaultdict(list)
        for meter_name, messages in self.messages.items():
            self.event[meter_name] = sorted((Sample(None, m) for m in messages), key=attrgetter("timestamp"))
            self.timestamps[meter_name] = [self.parse_timestamp(event.timestamp) for event in self.event[meter_name]]

    def usage(self, tenant_id, meter_name, start, end, limit=None):
        import bisect
        left = bisect.bisect_left(self.timestamps[meter_name], start)
        right = bisect.bisect_right(self.timestamps[meter_name], end)
        return self.event[meter_name][left:right]


class OpenStackUser:
    def __init__(self, name, password, email, tenant_id, enabled=True, user_id=None):
        self.user_id = user_id or Service.uuid_hash(name)
        self.name = name
        self.password = password
        self.email = email
        self.tenant_id = tenant_id
        self.enabled = enabled

    def __str__(self):
        return "<OpenStackUser %s %s>" % (self.user_id, self.name)


class OpenStackTenant:
    def __init__(self, name, description, enabled=True, tenant_id=None):
        self.tenant_id = tenant_id or Service.uuid_hash(name)
        self.name = name
        self.description = description
        self.enabled = enabled

    def __str__(self):
        return "<OpenStackTenant %s %s>" % (self.tenant_id, self.name)


class OpenStackStub():
    default_start_time = datetime.datetime(2015, 1, 1)
    default_end_time = datetime.datetime(2015, 6, 1)

    def __init__(self, start_time=None):
        if start_time is not None:
            self.start_time = start_time
        else:
            self.start_time = self.default_start_time

        tenant = Tenant("default_tenant", self.start_time)
        self.disk = Disk(tenant, "default_disk", self.start_time, 3*GB)
        self.volume = Volume(tenant, "default_volume", self.start_time, 5*GB)
        self.instance = Instance(tenant, "default_instance", Flavors.tiny)

