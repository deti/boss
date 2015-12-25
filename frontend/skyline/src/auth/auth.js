const dependencies = [
  require('./AuthorizationCtrl').default.name
];

export default angular.module('skyline.authorization', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('auth', {
      parent: 'boss-clean',
      url: '/authorization',
      views: {
        'main@boss-clean': {
          controller: 'AuthorizationCtrl',
          template: require('./auth.tpl.html')
        }
      },
      data: {
        bodyClassname: 'body-auth',
        pageTitle: 'Sign in'
      }
    });
  });
