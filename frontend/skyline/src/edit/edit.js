const dependencies = [
  require('../../../shared/skyline/servers/server.editBackupsCtrl').default.name,
  require('./SimpleServerEditCtrl').default.name
];

export default angular.module('skyline.simple.edit', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.simple.edit', {
        url: '/{id}',
        views: {
          'main@boss': {
            controller: 'SimpleServerEditCtrl',
            template: require('./edit.tpl.html')
          },
          'backups@openstack.simple.edit': {
            controller: 'OSServersEditBackupsCtrl',
            template: require('../../../shared/skyline/servers/server.backups.tpl.html')
          }
        },
        data: {
          pageTitle: 'Server settings'
        },
        resolve: {
          server: function ($stateParams, osServices) {
            return osServices.Nova.server($stateParams.id);
          },
          backups: function ($stateParams, osServices) {
            return osServices.Mistral.backupsForServer($stateParams.id);
          },
          images: function (osServices) {
            return osServices.Glance.images({status: 'active'});
          }
        }
      });
  });
