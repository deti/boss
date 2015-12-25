const dependencies = [
  require('./StatusCtrl').default.name
];

export default angular.module('skyline.simple.list', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.simple', {
        url: 'status',
        views: {
          'main@boss': {
            controller: 'StatusCtrl',
            template: require('./status.tpl.html')
          }
        },
        data: {
          pageTitle: 'Servers'
        },
        resolve: {
          servers: function (osServices) {
            return osServices.Nova.servers();
          }
        }
      });
  });
