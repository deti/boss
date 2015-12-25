const dependencies = [
  require('../../lib/userService/userService').default.name,
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../../shared/openstackService/openstackService').default.name,
  require('../../../shared/skyline/servers/skyline.servers').default.name,
  require('../../../shared/skyline/images/skyline.images').default.name,
  require('../../../shared/skyline/volumes/skyline.volumes').default.name,
  require('../../../shared/skyline/network/skyline.ips').default.name,
  require('../../../shared/skyline/backup/skyline.backup').default.name,
  require('../../../shared/skyline/dns/skyline.dns').default.name,
  require('../../../shared/skyline/ptr/skyline.ptr').default.name
];

export default angular.module('boss.lk.openstack', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('openstack', {
        parent: 'boss',
        url: '/openstack/',
        views: {
          'main@boss': {
            controller: 'OpenstackCtrl',
            template: require('./openstack.main.tpl.html')
          }
        },
        data: {
          pageTitle: 'Management'
        },
        resolve: {
          osServices: function (OSService, userService, popupErrorService, $state) {
            return userService.osToken()
              .then(OSService.getModules)
              .catch(rsp => {
                popupErrorService.show(rsp.data);
                $state.go('main');
              });
          }
        }
      });
  })
  .controller('OpenstackCtrl', function ($scope, $state) {
    if ($state.is('openstack')) {
      $state.go('openstack.servers.list');
    }
  });
