const dependencies = [
  require('./dns.listCtrl').default.name
];

export default angular.module('skyline.dns.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.dns', {
        url: 'dns',
        abstract: true
      })
      .state('openstack.dns.domains', {
        url: '/domains',
        views: {
          'main@boss': {
            controller: 'OSDomainsCtrl',
            template: require('./domains.tpl.html')
          }
        },
        data: {
          pageTitle: 'DNS'
        },
        resolve: {
          domains: function (osServices) {
            return osServices.Designate.domains()
              .then(osServices.DesignateV2.filterNotPtrZones);
          }
        }
      });
  });
