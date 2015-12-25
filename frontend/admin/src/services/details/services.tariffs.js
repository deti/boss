const dependencies = [
  require('../../../lib/serviceService/serviceService').default.name
];

export default angular.module('boss.admin.services.tariffs', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('services.details.tariffs', {
        url: '/tariffs',
        views: {
          'detail': {
            template: require('./services.tariffs.tpl.html'),
            controller: 'ServicesDetailsTariffsCtrl'
          }
        },
        resolve: {
          tariffs: function (serviceService, service) {
            return serviceService.tariffsWithService(service);
          }
        }
      });
  })
  .controller('ServicesDetailsTariffsCtrl', function ($scope, tariffs, $filter) {
    $scope.tariffs = tariffs;
    $scope.columns = [
      {
        field: 'title',
        title: $filter('translate')('Plan name'),
        sortDefault: true,
        template: '<a class="dashed" ui-sref="tariffs.details({id: item.tariff_id})">{{::item|localizedName}}</a>'
      },
      {
        field: 'users',
        title: $filter('translate')('Plan customers'),
        template: '<a class="dashed" ui-sref="main({tariff_ids: item.tariff_id})" ng-click="; $event.stopPropagation();">{{item.users}}</a>'
      }
    ];
  });
