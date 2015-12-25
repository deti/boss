const dependencies = [
  require('./server.newCtrl').default.name
];

export default angular.module('skyline.servers.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.servers.new', {
        //parent: 'openstack',
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSServersNewCtrl',
            template: require('./server.new.tpl.html')
          }
        },
        data: {
          pageTitle: 'New server'
        },
        params: {
          imageRef: null,
          flavorRef: null,
          volume_size: null,
          snapshotRef: null,
          source_type: 'image'
        },
        resolve: {
          keypairs: function (osServices) {
            return osServices.Nova.keypairs();
          },
          flavors: function (osServices) {
            return osServices.Nova.publicFlavors();
          },
          images: function (osServices) {
            return osServices.Nova.images();
          },
          servers: function () {
            return null;
          },
          networks: function (osServices) {
            return osServices.Neutron.networks();
          },
          snapshots: function (osServices, SNAPSHOT_STATUS) {
            return osServices.Cinder.snapshots({status: SNAPSHOT_STATUS.available.value});
          },
          volumes: function (osServices, VOLUME_STATUS) {
            return osServices.Cinder.volumes(false, {status: VOLUME_STATUS.available.value});
          },
          limits: function (osServices) {
            return osServices.Nova.limits();
          }
        }
      });
  });
