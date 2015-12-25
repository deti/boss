const dependencies = [
  require('./volumes.new').default.name
];

export default angular.module('skyline.volumes.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.volumes.new', {
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSVolumesNewCtrl',
            template: require('./volumes.new.tpl.html')
          }
        },
        data: {
          pageTitle: 'Volumes'
        },
        resolve: {
          servers: function (osServices) {
            return osServices.Nova.servers();
          },
          limits: function (osServices) {
            return osServices.Cinder.limits();
          }
        }
      });
  });
