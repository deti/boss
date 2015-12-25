const dependencies = [
  require('./SignupFinishedCtrl').default.name
];

export default angular.module('boss.lk.signupFinished', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signupFinished', {
      parent: 'boss-clean',
      url: '/signup-finished',
      views: {
        'main@boss-clean': {
          controller: 'SignupFinishedCtrl',
          template: require('./signupFinished.tpl.html')
        }
      },
      params: {
        user: null
      },
      data: {
        bodyClassname: 'body-auth',
        pageTitle: 'Registration'
      }
    });
  });
