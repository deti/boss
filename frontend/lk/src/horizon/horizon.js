const dependencies = [];

export default angular.module('boss.lk.horizon', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('horizon', {
      parent: 'openstack',
      url: 'horizon',
      views: {
        'main@boss': {
          template: require('./horizon.tpl.html')
        }
      },
      data: {
        pageTitle: 'My cloud',
        bodyClassname: 'mainview-full-height g-horizon'
      },
      resolve: {
        OSLogin: function (userService, $state) {
          return userService.OSLogin()
            .catch(e => {
              $state.go('main');
            });
        }
      }
    });
  });
