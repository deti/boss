const dependencies = [
  'toaster',
  require('../../../lib/categoriesWithServicesService/categoriesWithServicesService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];
const headerTplPath = require('./tariffs.new.services-header.partial.tpl.html');

export default angular.module('boss.admin.tariffs.new.services', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.new.services', {
        url: '/new',
        views: {
          'detail': {
            template: require('./tariffs.new.services.tpl.html'),
            controller: 'TariffsNewServicesCtrl'
          },
          'categories@tariffs.new.services': {
            template: require('../details/categories.edit.tpl.html')
          }
        },
        params: {
          newTariff: null
        },
        data: {
          detailsWide: true
        }
      });
  })
  .controller('TariffsNewServicesCtrl', function ($scope, $state, $filter, categoriesData, tariffService, toaster, tariffsFullList, categoriesWithServicesService, popupErrorService, newTariff) {
    $scope.customDetailsHeader.tpl = headerTplPath;
    $scope.tariff = newTariff;

    if ($scope.tariff.categories) {
      $scope.categories = $scope.tariff.categories;
    } else {
      $scope.categories = categoriesData;
      $scope.tariff.categories = categoriesData;
    }

    $scope.customDetailsHeader.countSelectedServices = function () {
      var count = 0;
      $scope.categories.forEach(category => {
        category.services.forEach(service => {
          if (service.selected) {
            count = count + 1;
          }
        });
      });
      return count;
    };

    var parentTariff;

    function setParentServices(id) {
      eraseSelectedServices($scope.categories);
      parentTariff = _.findWhere(tariffsFullList, {tariff_id: parseInt(id)});
      $scope.categories = categoriesWithServicesService.mergeTariffServices(parentTariff.services, $scope.categories);
    }

    function eraseSelectedServices(categories) {
      categories.forEach(category => {
        category.services.forEach(service => {
          service.selected = false;
          service.price = 0;
        });
      });
    }

    if ($scope.tariff.newParent && ($scope.tariff.newParent !== $scope.tariff.currentParent)) {
      $scope.tariff.currentParent = $scope.tariff.newParent;
      setParentServices($scope.tariff.currentParent);
    }

    $scope.customDetailsHeader.createTariff = function () {
      tariffService.createTariff($scope.tariff, $scope.categories)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Plan is successfully created'));
          $state.go('tariffs', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };
  });
