const dependencies = [
  require('./tariffs.new.1').default.name,
  require('./tariff.new.services').default.name,
  require('../../../lib/categoriesWithServicesService/categoriesWithServicesService').default.name
];

export default angular.module('boss.admin.tariffs.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.new', {
        abstract: true,
        views: {
          'details@boss': {
            template: require('../../details/details.tpl.html'),
            controller: 'TariffsNewCtrl'
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'New plan'
        },
        params: {
          parentId: null,
          newTariff: null
        },
        resolve: {
          categoriesData: function (categoriesWithServicesService) {
            return categoriesWithServicesService.get();
          },
          newTariff: function ($stateParams) {
            var newTariff = {};
            if ($stateParams.parentId) {
              newTariff.newParent = $stateParams.parentId;
            }
            if ($stateParams.newTariff) {
              newTariff = $stateParams.newTariff;
            }
            return newTariff;
          }
        }
      });
  })
  .controller('TariffsNewCtrl', function ($scope, $controller, $filter, newTariff, $state) {
    $scope.manyTabs = false;
    $scope.defaultState = 'tariffs.new.1';
    $scope.thisState = 'tariffs.new';
    angular.extend(this, $controller('DetailsBaseCtrl', {$scope: $scope}));
    $scope.tabs = [
      {
        title: $filter('translate')('Step 1 - Information'), state: 'tariffs.new.1', go: function () {
        $state.go('tariffs.new.1', {newTariff: newTariff});
      }
      },
      {
        title: $filter('translate')('Step 2 - Services'), state: 'tariffs.new.services', go: function () {
        $state.go('tariffs.new.services', {newTariff: newTariff});
      }
      }
    ];
  });
