const dependencies = [
  require('../../../lib/currencyService/currencyService').default.name
];

export default angular.module('boss.admin.tariffs.new1', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.new.1', {
        url: '/new',
        views: {
          'detail': {
            template: require('./tariffs.new.1.tpl.html'),
            controller: 'TariffsNewStepOneCtrl'
          }
        },
        params: {
          parentId: null,
          newTariff: null
        },
        resolve: {
          activeCurrency: function (currencyService) {
            return currencyService.activeCurrency();
          }
        }
      });
  })
  .controller('TariffsNewStepOneCtrl', function ($scope, $state, activeCurrency, tariffsFullList, $stateParams, newTariff) {
    $scope.tariff = newTariff;
    $scope.parentTariffs = tariffsFullList;
    $scope.activeCurrency = activeCurrency;

    $scope.$watch('tariff.newParent', function (newValue) {
      if (newValue) {
        var parent = _.findWhere(tariffsFullList, {tariff_id: parseInt(newValue)});
        $scope.tariff.currency = parent.currency;
      }
    });

    $scope.next = function () {
      if ($state.current.name === 'tariffs.new.1') {
        $state.go('tariffs.new.services', {newTariff: newTariff});
      }
    };
    $scope.cancel = function () {
      $state.go('tariffs', {}, {reload: true});
    };
  });
