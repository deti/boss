const dependencies = [];

export default angular.module('boss.error', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('error', {
      parent: 'boss-base',
      url: '/error',
      views: {
        'header@error': {
          template: ''
        },
        'layout@': {
          template: require('./layout.tpl.html')
        },
        'main@error': {
          template: require('./error.tpl.html')
        }
      },
      data: {
        pageTitle: 'Error',
        bodyClassname: 'body-auth'
      }
    });
  });
