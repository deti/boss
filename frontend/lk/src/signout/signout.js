const dependencies = [
  require('./SignoutCtrl').default.name
];

export default angular.module('boss.lk.signout', dependencies)
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
  });
