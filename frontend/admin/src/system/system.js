const dependencies = [
  require('./SystemCtrl').default.name
];

export default angular.module('boss.admin.system', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('system', {
        parent: 'boss',
        url: '/test-email',
        views: {
          'main@boss': {
            controller: 'SystemCtrl',
            template: require('./system.tpl.html')
          }
        },
        data: {
          pageTitle: 'System'
        },
        resolve: {}
      });
  });
