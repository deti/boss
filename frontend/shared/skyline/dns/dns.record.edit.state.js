const dependencies = [
  require('./dns.record.editCtrl').default.name
];

export default angular.module('skyline.dns.record.edit.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.dns.records.edit', {
        url: '/{recordId}',
        views: {
          'main@boss': {
            controller: 'OSRecordEditCtrl',
            template: require('./edit.record.tpl.html')
          }
        },
        resolve: {
          domain: function (osServices, $stateParams) {
            return osServices.Designate.domain($stateParams.domainId);
          },
          record: function (osServices, $stateParams) {
            return osServices.Designate.record($stateParams.domainId, $stateParams.recordId);
          }
        },
        data: {
          pageTitle: 'DNS'
        }
      });
  });
