const dependencies = [
  require('./ips.newCtrl').default.name
];

export default angular.module('skyline.ips.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.ips.new', {
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSIPsNewCtrl',
            template: require('./ips.new.tpl.html')
          }
        },
        data: {
          pageTitle: 'IP-addresses'
        },
        resolve: {
          floatingIPPools: function (osServices) {
            return osServices.Nova.floatingIPPools();
          },
          limits: function (osServices) {
            return osServices.Nova.limits();
          }
        },
        params: {
          returnUrl: null
        }
      });
  });
