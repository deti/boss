const dependencies = [
  require('./CardsCtrl').default.name,
  require('../../lib/payService/payService').default.name
];

export default angular.module('boss.lk.cards', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('cards', {
      parent: 'boss',
      url: '/cards',
      views: {
        'main@boss': {
          controller: 'CardsCtrl',
          template: require('./cards.tpl.html')
        }
      },
      data: {
        pageTitle: 'My cards'
      },
      resolve: {
        cardsList: function (payService) {
          return payService.cardsList();
        }
      }
    });
  });
