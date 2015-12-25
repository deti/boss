const dependencies = [
  require('./server.listCtrl').default.name
];

export default angular.module('skyline.servers.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.servers', {
        url: 'servers',
        abstract: true
      })
      .state('openstack.servers.list', {
        url: '/',
        views: {
          'main@boss': {
            controller: 'OSServersListCtrl',
            template: require('./server.list.tpl.html')
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
