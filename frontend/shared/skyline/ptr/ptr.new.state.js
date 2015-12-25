const dependencies = [
  require('./ptr.new').default.name
];

export default angular.module('skyline.ptr.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.ptr.new', {
        url: '/new?serverId',
        views: {
          'main@boss': {
            controller: 'PTRNewCtrl',
            template: require('./ptr.new.tpl.html')
          }
        },
        data: {
          pageTitle: 'Create PTR record'
        },
        resolve: {
          zones: function (osServices) {
            return osServices.DesignateV2.zones()
              .then(osServices.DesignateV2.filterNotPtrZones);
          },
          ips: function (osServices) {
            return osServices.Nova.usedIPs();
          }
        }
      });
  });
