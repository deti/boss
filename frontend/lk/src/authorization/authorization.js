const dependencies = [
  require('../signin/signin').default.name
];

export default angular.module('boss.lk.authorization', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('authorization', {
      parent: 'boss-clean',
      url: '/authorization',
      views: {
        'main@boss-clean': {
          controller: 'AuthorizationCtrl',
          template: require('./authorization.tpl.html')
        }
      },
      data: {
        bodyClassname: 'body-auth'
      }
    });
  })
  .controller('AuthorizationCtrl', function ($scope, $rootScope, $state) {
    if ($state.current.name === 'authorization') {
      $state.go('signin');
    }
  });
