const dependencies = [
  require('./Production2Ctrl').default.name
];

export default angular.module('boss.lk.production.step2', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('production2', {
        parent: 'boss',
        url: '/production-step2',
        views: {
          'main@boss': {
            template: require('./production.step2.tpl.html'),
            controller: 'Production2Ctrl'
          }
        },
        data: {
          pageTitle: 'Working mode'
        },
        resolve: {
          payScript: function (payService) {
            return payService.load();
          }
        }
      });
  });
