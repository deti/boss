const dependencies = [
  require('../../../lib/categoriesWithServicesService/categoriesWithServicesService').default.name
];
const headerTplPath = require('./tariffs.services-header.partial.tpl.html');

export default angular.module('boss.admin.tariffs.services', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.details.services', {
        url: '/services',
        views: {
          'detail': {
            controller: 'TariffDetailsServicesWrapperCtrl'
          }
        },
        resolve: {
          categoriesData: function (categoriesWithServicesService) {
            return categoriesWithServicesService.get();
          }
        }
      })
      .state('tariffs.details.services.edit', {
        views: {
          'detail@tariffs.details': {
            template: require('./tariffs.services.tpl.html'),
            controller: 'TariffsDetailsServicesEditCtrl'
          },
          'categories@tariffs.details.services.edit': {
            template: require('./categories.edit.tpl.html')
          }
        },
        data: {
          detailsWide: true
        }
      })
      .state('tariffs.details.services.readOnly', {
        views: {
          'detail@tariffs.details': {
            template: require('./tariffs.services.readOnly.tpl.html'),
            controller: 'TariffsDetailsServicesReadOnlyCtrl'
          }
        }
      });
  })
  .controller('TariffsDetailsServicesEditCtrl', function ($scope, $state, $filter, $controller, Restangular, tariff, categoriesData, categoriesWithServicesService, tariffService, toaster, TARIFF_STATE, popupErrorService) {
    $scope.customDetailsHeader.tpl = headerTplPath;

    $scope.tariff = Restangular.copy(tariff);
    $scope.categories = categoriesWithServicesService.mergeTariffServices($scope.tariff.services, categoriesData);

    $scope.checkSelectedServices = function (category) {
      var selected = _.find(category.services, service => service.selected === true);
      return !!selected;
    };

    var selectedCategoriesClone = [];
    $scope.categories.forEach(category => {
      if ($scope.checkSelectedServices(category)) {
        selectedCategoriesClone.push(angular.copy(category));
      }
    });

    $scope.customDetailsHeader.update = function () {
      tariffService.updateTariff({tariff_id: $scope.tariff.tariff_id}, $scope.categories)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Plan is successfully changed'));
          $state.go('tariffs', {}, {reload: true});
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };
  })
  .controller('TariffsDetailsServicesReadOnlyCtrl', function ($scope, $state, $filter, Restangular, tariff, categoriesData, categoriesWithServicesService, tariffService, toaster, TARIFF_STATE, popupErrorService) {
    $scope.customDetailsHeader.tpl = null;
    $scope.tariff = Restangular.copy(tariff);
    $scope.categories = categoriesWithServicesService.mergeTariffServices($scope.tariff.services, categoriesData);

    $scope.checkSelectedServices = function (category) {
      var selected = _.find(category.services, service => service.selected === true);
      return !!selected;
    };

    var selectedCategoriesClone = [];
    $scope.categories.forEach(category => {
      if ($scope.checkSelectedServices(category)) {
        selectedCategoriesClone.push(angular.copy(category));
      }
    });

    $scope.updateMutableServices = function (form) {
      tariffService.updateMutableServices($scope.tariff.tariff_id, $scope.categories, selectedCategoriesClone, form)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Plan is successfully changed'));
          $state.go('tariffs', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };
  })
  .controller('TariffDetailsServicesWrapperCtrl', function ($state, tariff, TARIFF_STATE) {
    if ($state.is('tariffs.details.services')) {
      var stateName = tariff.status.value === TARIFF_STATE.NEW.value ? 'tariffs.details.services.edit' : 'tariffs.details.services.readOnly';
      $state.go(stateName);
    }
  });
