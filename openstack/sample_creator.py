from neutronclient.v2_0.client import Client as neutronclient
from cinderclient.v2.client import Client as cinderclient
from ceilometerclient.client import get_client
from os import path

import yaml
import sys


class Creator(object):
    def __init__(self, auth):
        self.neutron = neutronclient(**auth)
        self.ceilometer = get_client(version=2, **auth)
        self.cinder = cinderclient(username=auth['username'], api_key=auth['password'], project_id=auth['tenant_name'],
                                   auth_url=auth['auth_url'])

    def get_floating_ips(self):
        return self.neutron.list_floatingips()['floatingips']

    def create_ip_samples(self):
        ips = self.get_floating_ips()
        for ip in ips:
            self.ceilometer.samples.create(
                counter_name='ip.floating',
                resource_id=ip['id'],
                counter_unit='ip',
                counter_volume=1,
                project_id=ip['tenant_id'],
                counter_type='gauge',
                metadata={
                    'address': ip['floating_ip_address']
                }
            )

    def get_volumes(self):
        search_opts = dict(all_tenants=True)
        return self.cinder.volumes.list(search_opts=search_opts)

    def create_volume_size_samples(self):
        volumes = self.get_volumes()
        for volume in volumes:
            self.ceilometer.samples.create(
                counter_name='volume.size',
                resource_id=volume.id,
                counter_unit='GB',
                counter_volume=volume.size,
                project_id=getattr(volume, 'os-vol-tenant-attr:tenant_id'),
                counter_type='gauge',
                metadata={
                    #'display_name': volume.display_name,
                    'availability_zone': volume.availability_zone
                }
            )

    def get_snapshots(self):
        search_opts = dict(all_tenants=True)
        return self.cinder.volume_snapshots.list(search_opts=search_opts)

    def create_snapshot_size_samples(self):
        snapshots = self.get_snapshots()
        for snapshot in snapshots:
            self.ceilometer.samples.create(
                counter_name='snapshot.size',
                resource_id=snapshot.id,
                counter_unit='GB',
                counter_volume=snapshot.size,
                project_id=snapshot.project_id,
                counter_type='gauge'
            )

    def run(self):
        self.create_ip_samples()
        self.create_volume_size_samples()
        self.create_snapshot_size_samples()

def main():
    pathname = path.dirname(sys.argv[0])
    cred_abs_path = path.abspath(pathname)
    with open(path.join(cred_abs_path, 'os_credentials.yaml'), 'r') as cred_file:
        auth = yaml.load(cred_file)
        creator = Creator(auth)
        creator.run()

if __name__ == "__main__":
    main()
