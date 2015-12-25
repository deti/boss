const dependencies = [
  require('./server.editCtrl').default.name,
  require('./server.editBackupsCtrl').default.name
];

export default angular.module('skyline.servers.edit.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.servers.edit', {
        url: '/{id}',
        views: {
          'main@boss': {
            controller: 'OSServersEditCtrl',
            template: require('./server.edit.tpl.html')
          },
          'backups@openstack.servers.edit': {
            controller: 'OSServersEditBackupsCtrl',
            template: require('./server.backups.tpl.html')
          }
        },
        data: {
          pageTitle: 'Management'
        },
        resolve: {
          server: function ($stateParams, osServices) {
            return osServices.Nova.server($stateParams.id);
          },
          flavors: function (osServices) {
            return osServices.Nova.publicFlavors();
          },
          volumes: function (server, osServices) {
            return osServices.Nova.serverLoadVolumes(server);
          },
          availableVolumes: function (osServices) {
            return osServices.Cinder.availableVolumes();
          },
          backups: function ($stateParams, osServices) {
            return osServices.Mistral.backupsForServer($stateParams.id);
          },
          ips: function (osServices, $stateParams) {
            return osServices.Nova.floatingIPs()
              .then(ips => {
                return _.filter(ips, ip => {
                  return !ip.instance_id || ip.instance_id === $stateParams.id;
                });
              });
          }
        }
      });
  });
