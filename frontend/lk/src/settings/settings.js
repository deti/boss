const dependencies = [
  require('./SettingsCtrl').default.name,
  require('../../lib/utilityService/utilityService').default.name,
  require('../../lib/userService/userService').default.name,
  require('../../lib/payService/payService').default.name,
  require('../../lib/bsStrongPasswordValidator/bsStrongPasswordValidator').default.name
];

export default angular.module('boss.lk.settings', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('settings', {
      parent: 'boss',
      url: '/settings',
      views: {
        'main@boss': {
          controller: 'SettingsCtrl',
          template: require('./settings.tpl.html'),
          resolve: {
            countries: function (utilityService) {
              return utilityService.countries();
            },
            subscriptions: function (userService) {
              return userService.subscriptions();
            },
            subscriptionsInfo: function (utilityService) {
              return utilityService.subscriptionsInfo();
            },
            locales: function (utilityService) {
              return utilityService.locales();
            },
            withdrawPeriods: function (utilityService) {
              return utilityService.withdrawPeriod('auto_report');
            },
            cardsList: function (payService) {
              return payService.cardsList();
            },
            withdrawParams: function (userService) {
              return userService.getAutoWithdraw();
            }
          }
        }
      },
      data: {
        pageTitle: 'Account settings'
      }
    });
  });
