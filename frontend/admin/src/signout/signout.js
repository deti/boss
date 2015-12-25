const dependencies = [
  require('../../lib/currentUserService/currentUserService').default.name
];

export default angular.module('boss.signout', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signout', {
      parent: 'boss',
      url: '/admin/signout',
      views: {
        'main@boss': {
          controller: 'SignoutCtrl'
        }
      },
      data: {
        pageTitle: 'Sign out'
      }
    });
  })
  .controller('SignoutCtrl', function ($scope, currentUserService, $state) {
    currentUserService.logout()
      .then(function () {
        $state.go('signin');
      });
  });
