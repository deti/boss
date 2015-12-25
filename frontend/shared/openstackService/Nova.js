const dependencies = [
  require('../urlParser/urlParser').default.name,
  require('./Cinder').default.name,
  require('./BaseOpenstack').default.name,
  require('./ServerModel').default.name
];

export default angular.module('boss.openstackService.Nova', dependencies)
  .value('SHOW_DISK_SIZE_IN_FLAVOR', true)
  .factory('Nova', function (BaseOpenstack, Cinder, $q, $filter, ServerModel, URLParser, SHOW_DISK_SIZE_IN_FLAVOR, OSCredentials) {
    /**
     * @augments BaseOpenstack
     */
    class Nova extends BaseOpenstack {
      constructor() {
        super('/nova/v2/{tenantId}/');
        this.Restangular.extendModel('servers/detail', ServerModel);
        this.Restangular.extendModel('servers', ServerModel);
        this.Restangular.addRequestInterceptor(function (elem, operation, what) {
          if (operation === 'put' && what === 'servers') {
            return {
              server: {
                name: elem.server.name,
                accessIPv4: elem.server.accessIPv4,
                accessIPv6: elem.server.accessIPv6,
                auto_disk_config: elem.server.auto_disk_config
              }
            };
          }
          if (operation === 'post' && what === 'servers') {
            if (elem.server.adminPass) {
              const postInstallScript = [
                '#cloud-config',
                `password: ${elem.server.adminPass}`,
                'chpasswd: { expire: False }',
                'ssh_pwauth: True'
              ].join('\n');
              delete elem.server.adminPass;
              elem.server.user_data = btoa(postInstallScript);
            }
          }
          return elem;
        });
      }

      servers(simple = false, allTenants = false) {
        return this.loadFullList(this.Restangular.all('servers/detail'), 'servers', {all_tenants: allTenants ? 1 : null})
          .then(servers => {
            if (simple) {
              return servers;
            }
            var allPromises = [];
            servers.forEach(server => {
              allPromises.push(this.serverLinkedData(server));
            });
            return $q.all(allPromises)
              .then(() => servers);
          });
      }

      server(serverId) {
        return this.Restangular.one('servers', serverId).get();
      }

      serverLoadFlavor(server) {
        if (server.flavor) {
          return this.loadLinkedData(server, 'flavor')
            .then(() => server);
        }
        return $q.when(server);
      }

      serverLoadImage(server) {
        if (server.image) {
          return this.loadLinkedData(server, 'image')
            .then(() => server);
        }
        return $q.when(server);
      }

      serverLoadVolumes(server) {
        if (server['os-extended-volumes:volumes_attached']) {
          var volumesPromises = server['os-extended-volumes:volumes_attached']
            .map(volumeInfo => {
              return Cinder.volume(volumeInfo.id)
                .catch(e => {
                  if (e.status === 404) {
                    return {notFound: true};
                  }
                });
            });
          return $q.all(volumesPromises)
            .then(volumes => server.volumes = volumes);
        }
        return $q.when(server);
      }

      serverLinkedData(server) {
        var promises = [
          this.serverLoadFlavor(server),
          this.serverLoadImage(server),
          this.serverLoadVolumes(server)
        ];
        return $q.all(promises)
          .then(() => server);
      }

      createServer(server) {
        return this.Restangular.all('servers').post({server});
      }

      flavors() {
        return this.loadFullList(this.Restangular.all('flavors/detail'), 'flavors')
          .then(flavors => {
            return _.sortByAll(flavors.map(item => {
              item.about = `CPU ${item.vcpus} | ` + $filter('bytes')(item.ram, 'MB') + ` RAM`;
              if (SHOW_DISK_SIZE_IN_FLAVOR) {
                item.about += ' | ' + $filter('bytes')(item.disk, 'GB');
              }
              item.about += ` (${item.name})`;
              return item;
            }), ['ram', 'vcpus']);
          });
      }

      publicFlavors() {
        return this.flavors()
          .then(flavors => {
            return _.filter(flavors, f => !f['os-flavor-access:is_public']);
          });
      }

      loadLinkedData(obj, property) {
        return this.load(this.processLinksUrl(obj[property].links[0].href))
          .then((data) => {
            obj[property] = data[property];
          })
          .catch(e => {
            if (e.status === 404) {
              obj[property].notFound = true;
            }
          });
      }

      processLinksUrl(url) {
        var parser = new URLParser(url);
        var pathname = parser.pathname
          .substring(1)
          .replace(OSCredentials.tenantId, '')
          .substring(1);
        return this.Restangular.baseUrl + pathname;
      }

      keypairs() {
        return this.loadFullList(this.Restangular.all('os-keypairs'), 'keypairs');
      }

      createKeypair(keypair) {
        return this.Restangular.all('os-keypairs').post({keypair});
      }

      images() {
        return this.loadFullList(this.Restangular.all('images'), 'images');
      }

      attachVolume(serverId, volumeId) {
        var volumeAttachment = {
          volumeId
        };
        return this.Restangular.one('servers', serverId).one('os-volume_attachments').customPOST({volumeAttachment});
      }

      detachVolume(serverId, volumeId) {
        return this.Restangular.one('servers', serverId).one('os-volume_attachments').one(volumeId).customDELETE();
      }

      floatingIPs() {
        return this.Restangular.all('os-floating-ips').getList()
          .then((ips) => {
            var promises = [];
            ips.forEach(ip => {
              if (ip.instance_id) {
                promises.push(this.server(ip.instance_id)
                  .then(server => {
                    ip.server = server.name;
                  }));
              }
            });
            return $q.all(promises).then(() => ips);
          });
      }

      floatingIPPools() {
        return this.Restangular.all('os-floating-ip-pools').getList();
      }

      allocateFloatingIP(pool) {
        return this.Restangular.one('os-floating-ips').customPOST({pool});
      }

      deallocateFloatingIP(ip) {
        return this.Restangular.one('os-floating-ips').one(ip.id).customDELETE();
      }

      removeFloatIPFromServer(ip) {
        return this.Restangular.one('servers', ip.instance_id).one('action').customPOST({
          removeFloatingIp: {
            address: ip.ip
          }
        });
      }

      limits() {
        return this.Restangular.one('limits').get()
          .then(r => {
            return r.limits;
          });
      }

      usedIPs() {
        return this.servers(true)
          .then(servers => {
            var ips = [];
            servers.forEach(server => {
              if (!server.addresses) {
                return;
              }
              var addresses = _.flatten(_.values(server.addresses));
              addresses.forEach(addr => {
                ips.push({
                  ip: addr.addr,
                  name: `${addr.addr} (${server.name})`,
                  server: server
                });
              });
            });
            return ips;
          });
      }
    }

    return new Nova();
  });
