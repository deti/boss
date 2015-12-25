const dependencies = [
  require('./dns.newCtrl').default.name
];

export default angular.module('skyline.dns.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.dns.domains.new', {
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSDomainNewCtrl',
            template: require('./new.domain.tpl.html')
          }
        },
        data: {
          pageTitle: 'DNS'
        }
      });
  });
