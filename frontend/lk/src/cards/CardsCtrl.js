const dependencies = [
  'toaster',
  require('../../lib/payService/payService').default.name
];

export default angular.module('boss.lk.CardsCtrl', dependencies)
  .controller('CardsCtrl', function CardsCtrl($scope, toaster, $filter, payService, cardsList) {
    $scope.removeCard = function removeCard(card) {
      payService.removeCard(card.card_id)
        .then(function () {
          toaster.pop('success', $filter('translate')('Bound card was successfully deleted'));
          _.remove(cardsList, item => item.card_id === card.card_id);
          $scope.data = cardsList;
        });
    };
    $scope.data = cardsList;
    $scope.columns = [
      {
        field: 'last_four',
        title: $filter('translate')('Card'),
        titleClass: 'no-sort',
        template: '**** **** {{::item.last_four}} {{::item.card_type}}'
      },
      {
        field: 'status', title: $filter('translate')('Status'), titleClass: 'no-sort'
      },
      {
        field: 'none',
        title: '',
        template: '<a href="#" ng-click="removeCard(item);" translate>Remove</a>',
        titleClass: 'no-sort'
      }
    ];
  });
