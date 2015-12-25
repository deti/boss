const dependencies = [
  require('../../../shared/openstackService/openstackService').default.name,
  require('../../../shared/skyline/images/skyline.images').default.name,
  require('../../../shared/skyline/backup/skyline.backup').default.name,
  require('../status/status').default.name,
  require('../edit/edit').default.name,
  require('../recreate/recreate').default.name,
  require('../ptr/skyline_standalone.ptr').default.name
];

export default angular.module('skyline.openstack', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack', {
        parent: 'boss',
        url: '/?token&tenantId',
        views: {
          'main@boss': {
            controller: 'OpenstackCtrl',
            template: require('./openstack.main.tpl.html')
          }
        },
        data: {
          pageTitle: 'Servers'
        },
        resolve: {
          osServices: function (OSService, $q, $stateParams, openstackAuth) {
            var d = $q.defer();
            var token = openstackAuth.isAuthenticated();
            if (!$stateParams.token && !token) {
              d.reject('should log in');
              return d.promise;
            }

            if ($stateParams.token) {
              token = $stateParams.token;
            } else if (!token) {
              d.reject('should log in');
              return d.promise;
            }
            openstackAuth.checkToken(token)
              .then(authPair => {
                d.resolve(OSService.getModules(authPair));
              })
              .catch(e => {
                d.reject('should log in');
              });
            return d.promise;
          }
        }
      })
      .state('openstack.servers', { // this state needed for openstack.servers.vnc. It will not work without parent state
        url: 'servers',
        abstract: true
      });
  })
  .value('imgActionTpl', require('./images.cell.actions.partial.tpl.html'))
  .value('snapshotActionsTpl', require('./snapshot.cell.actions.partial.tpl.html'))
  .controller('OpenstackCtrl', function ($scope, $state) {
    if ($state.is('openstack')) {
      $state.go('openstack.simple', {token: null, tenantId: null});
    }
  });
