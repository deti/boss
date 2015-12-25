const dependencies = [
  require('./volumes.listCtrl').default.name
];

export default angular.module('skyline.volumes.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.volumes', {
        url: 'volumes',
        views: {
          'main@boss': {
            controller: 'OSVolumesListCtrl',
            template: require('./volumes.list.tpl.html')
          }
        },
        data: {
          pageTitle: 'Volumes'
        },
        resolve: {
          volumes: function (osServices) {
            return osServices.Cinder.volumes();
          },
          servers: function (osServices) {
            return osServices.Nova.servers(true);
          }
        }
      });
  });
