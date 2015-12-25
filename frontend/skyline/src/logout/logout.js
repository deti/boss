const dependencies = [
  require('../openstackAuth/openstackAuth').default.name
];

export default angular.module('skyline.logout', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signout', {
      parent: 'boss',
      url: '/signout',
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
  .controller('SignoutCtrl', function ($scope, openstackAuth, $state) {
    openstackAuth.logout();
    $state.go('auth');
  });
