const dependencies = [
  require('./ProductionCtrl').default.name,
  require('../../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.lk.production', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('production', {
        parent: 'boss',
        url: '/production',
        views: {
          'main@boss': {
            template: require('./production.tpl.html'),
            controller: 'ProductionCtrl'
          }
        },
        resolve: {
          countries: function (utilityService) {
            return utilityService.countries();
          }
        },
        data: {
          pageTitle: 'Working mode',
          bodyClassname: 'g-test-banner-hidden'
        }
      });
  });
