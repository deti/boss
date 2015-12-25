const dependencies = [
  require('./PayCtrl').default.name,
  require('../../lib/payService/payService').default.name
];

export default angular.module('boss.lk.pay', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('pay', {
      parent: 'boss',
      url: '/pay',
      views: {
        'main@boss': {
          controller: 'PayCtrl',
          template: require('./pay.tpl.html')
        }
      },
      data: {
        pageTitle: 'Replenishment'
      },
      resolve: {
        payScript: function (payService) {
          return payService.load();
        },
        cardsList: function (payService) {
          return payService.cardsList();
        }
      }
    });
  });
