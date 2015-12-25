const dependencies = [
  require('../accountInfo/accountInfo').default.name,
  require('./MainCtrl').default.name,
  require('../../lib/userService/userService').default.name,
  require('../../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.lk.main', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('main', {
        parent: 'boss',
        url: '/index?after?before',
        views: {
          'main@boss': {
            controller: 'MainCtrl',
            template: require('./main.tpl.html')
          },
          'info@main': {
            template: require('../accountInfo/accountInfo.tpl.html'),
            controller: 'AccountInfoCtrl'
          },
          'limits@main': {
            template: require('./main.limits.tpl.html')
          }
        },
        resolve: {
          tariff: function (userService) {
            return userService.tariff();
          },
          quotas: function (userService) {
            return userService.usedQuotas();
          },
          period: function (utilityService, userInfo) {
            return utilityService.getLocalizedPeriod(userInfo.withdraw_period);
          },
          uInfoReload: function (userService, userInfo) {
            return userService.reload(userInfo);
          }
        },
        data: {
          pageTitle: 'Main'
        }
      });
  });
