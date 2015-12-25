const dependencies = [
  require('./dns.recordsCtrl').default.name
];

export default angular.module('skyline.dns.records.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.dns.records', {
        url: '/:domainId/records',
        views: {
          'main@boss': {
            controller: 'OSRecordsCtrl',
            template: require('./records.tpl.html')
          }
        },
        data: {
          pageTitle: 'DNS'
        },
        resolve: {
          domain: function (osServices, $stateParams) {
            return osServices.Designate.domain($stateParams.domainId);
          },
          records: function (osServices, $stateParams) {
            return osServices.Designate.records($stateParams.domainId);
          }
        }
      });
  });
