const dependencies = [
  'restangular',
  'toaster',
  require('../../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../../lib/currencyService/currencyService').default.name,
  require('../../../lib/tariffService/tariffService').default.name
];

export default angular.module('boss.admin.tariffs.info', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.details.info', {
        url: '/info',
        views: {
          'detail': {
            template: require('./tariffs.info.tpl.html'),
            controller: 'TariffsDetailsInfoCtrl'
          }
        },
        resolve: {
          activeCurrency: function (currencyService) {
            return currencyService.activeCurrency();
          }
        }
      });
  })
  .controller('TariffsDetailsInfoCtrl', function ($scope, $state, activeCurrency, $filter, Restangular, tariff, tariffsFullList, tariffService, toaster, TARIFF_STATE, popupErrorService) {
    $scope.customDetailsHeader.tpl = null;
    $scope.params = Restangular.copy(tariff);
    $scope.statusName = $filter('localizedName')($scope.params.status);
    $scope.activeCurrency = activeCurrency;
    var parentTariff;

    if ($scope.params) {
      if ($scope.params.parent_id) {
        parentTariff = _.findWhere(tariffsFullList, {tariff_id: parseInt($scope.params.parent_id)});
        $scope.params.parentName = $filter('localizedName')(parentTariff);
      } else {
        $scope.params.parentName = $filter('localizedName')({localized_name: {en: 'No', ru: 'No'}});
      }
    }

    $scope.isNew = function () {
      return $scope.params.status.value === TARIFF_STATE.NEW.value;
    };

    $scope.isActive = function () {
      return $scope.params.status.value === TARIFF_STATE.ACTIVE.value;
    };

    $scope.isArchived = function () {
      return $scope.params.status.value === TARIFF_STATE.ARCHIVED.value;
    };

    $scope.createWithParent = function () {
      $state.go('tariffs.new.1', {parentId: $scope.params.tariff_id});
    };

    $scope.update = function (form) {
      tariffService.updateTariff($scope.params, null)
        .then(function (rsp) {
          Restangular.sync(rsp.tariff_info, tariff);
          toaster.pop('success', $filter('translate')('Plan is successfully changed'));
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.archive = function () {
      tariffService.archiveTariff($scope.params.tariff_id)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Plan is moved to archive'));
          $state.go('tariffs', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.setDefault = function () {
      tariffService.defaultTariff($scope.params.tariff_id)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Default plan is assigned'));
          $state.go('tariffs', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.activate = function () {
      tariffService.activateTariff($scope.params.tariff_id)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Plan has the "Current" status'));
          $state.go('tariffs', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };
  });
