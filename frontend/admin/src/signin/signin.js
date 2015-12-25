const dependencies = [
  require('./SigninCtrl').default.name
];

export default angular.module('boss.admin.signin', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signin', {
      parent: 'boss-clean',
      url: '/signin',
      views: {
        'main@boss-clean': {
          controller: 'SigninCtrl',
          template: require('./signin.tpl.html')
        }
      },
      data: {
        pageTitle: 'Sign in',
        bodyClassname: 'body-gray auth-view'
      },
      params: {
        returnState: null,
        returnParams: null
      }
    });
  });
