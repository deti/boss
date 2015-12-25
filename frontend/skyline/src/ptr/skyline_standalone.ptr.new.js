const dependencies = [
  require('../../../shared/skyline/ptr/ptr.new').default.name,
  require('../../../shared/bsEndWith/bsEndWith').default.name,
  require('../../../shared/bsDomainName/bsDomainName').default.name
];

export default angular.module('skyline_standalone.ptr.new.state', dependencies)
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
          },
          userInfo: function () {
            return {email: 'tech@firstbyte.ru'};
          }
        }
      });
  });
