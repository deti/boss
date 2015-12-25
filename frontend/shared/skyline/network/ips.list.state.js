const dependencies = [
  require('./ips.listCtrl').default.name
];

export default angular.module('skyline.ips.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.ips', {
        url: 'ips',
        views: {
          'main@boss': {
            controller: 'OSIPsCtrl',
            template: require('./ips.tpl.html')
          }
        },
        data: {
          pageTitle: 'IP-addresses'
        },
        resolve: {
          servers: function (osServices) {
            return osServices.Nova.servers(true);
          },
          floatingIPs: function (osServices) {
            return osServices.Nova.floatingIPs();
          }
        }
      });
  });
