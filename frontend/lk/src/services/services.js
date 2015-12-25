const dependencies = [
  require('../accountInfo/accountInfo').default.name,
  require('./ServicesCtrl').default.name,
  require('../../lib/userService/userService').default.name,
  require('../../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.lk.services', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('services', {
      parent: 'boss',
      url: '/services',
      views: {
        'main@boss': {
          controller: 'ServicesCtrl',
          template: require('./services.tpl.html'),
          resolve: {
            tariff: function (userService) {
              return userService.tariff();
            },
            period: function (utilityService, userInfo) {
              return utilityService.getLocalizedPeriod(userInfo.withdraw_period);
            },
            uInfoReload: function (userService, userInfo) {
              return userService.reload(userInfo);
            }
          }
        },
        'info@services': {
          template: require('../accountInfo/accountInfo.tpl.html'),
          controller: 'AccountInfoCtrl'
        }
      },
      data: {
        pageTitle: 'Services'
      }
    });
  });
