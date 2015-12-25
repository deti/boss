const dependencies = [];

export default angular.module('boss.admin.FlavorsDetailsTariffsCtrl', dependencies)
  .controller('FlavorsDetailsTariffsCtrl', function FlavorsDetailsTariffsCtrl($scope, tariffs, $filter) {
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
