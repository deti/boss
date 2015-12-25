const dependencies = [
  require('./ptr.editCtrl').default.name,
  require('../../bsDomainName/bsDomainName').default.name
];

export default angular.module('skyline.ptr.edit.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.ptr.edit', {
        url: '/{id}',
        views: {
          'main@boss': {
            controller: 'PTREditCtrl as editCtrl',
            template: require('./ptr.edit.tpl.html')
          }
        },
        data: {
          pageTitle: 'PTR'
        },
        resolve: {
          zone: function (osServices, $stateParams) {
            return osServices.DesignateV2.zone($stateParams.id);
          },
          recordsets: function (osServices, zone) {
            return osServices.DesignateV2.zoneRecordsets(zone);
          }
        }
      });
  });
