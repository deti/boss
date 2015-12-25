const dependencies = [
  require('./ptr.listCtrl').default.name
];

export default angular.module('skyline.ptr.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.ptr', {
        url: 'ptr',
        views: {
          'main@boss': {
            controller: 'PTRListCtrl',
            template: require('./ptr.list.tpl.html')
          }
        },
        data: {
          pageTitle: 'PTR'
        },
        resolve: {
          zones: function (osServices) {
            return osServices.DesignateV2.zones()
              .then(osServices.DesignateV2.filterPtrZones)
              .then(osServices.DesignateV2.zonesRecordsets.bind(osServices.DesignateV2));
          },
          ips: function (osServices) {
            return osServices.Nova.usedIPs();
          }
        }
      });
  });
