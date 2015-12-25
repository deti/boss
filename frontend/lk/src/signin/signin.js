const dependencies = [
  require('./SigninCtrl').default.name
];

export default angular.module('boss.lk.signin', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signin', {
      parent: 'authorization',
      url: '/signin',
      views: {
        'form@authorization': {
          controller: 'SigninCtrl',
          template: require('./signin.tpl.html')
        }
      },
      data: {
        pageTitle: 'Sign in'
      },
      params: {
        returnState: null,
        returnParams: null
      }
    });
  });
