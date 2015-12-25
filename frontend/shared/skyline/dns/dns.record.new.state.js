const dependencies = [
  require('./dns.record.newCtrl').default.name
];

export default angular.module('skyline.dns.record.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.dns.records.new', {
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSRecordNewCtrl',
            template: require('./new.record.tpl.html')
          }
        },
        resolve: {
          domain: function (osServices, $stateParams) {
            return osServices.Designate.domain($stateParams.domainId);
          }
        },
        data: {
          pageTitle: 'DNS'
        }
      });
  });
