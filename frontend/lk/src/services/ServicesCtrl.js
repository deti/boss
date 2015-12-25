const dependencies = [];

export default angular.module('boss.lk.ServicesCtrl', dependencies)
  .controller('ServicesCtrl', function ServicesCtrl($scope, $filter, tariff, userInfo, period) {
    $scope.user = userInfo;
    $scope.tariff = tariff;
    $scope.period = period;
    $scope.showState = false;

    $scope.columns = [
      {
        field: 'service',
        title: $filter('translate')('Services included in your plan'),
        filter: 'localizedName',
        defaultSort: true,
        template: '<span title="{{::item.service | localizedName}}">{{::item.service | localizedName}}</span>',
        width: 300
      },
      {
        field: 'service.measure',
        title: $filter('translate')('Measurement units'),
        filter: 'localizedName',
        width: 170
      },
      {
        field: 'price',
        title: $filter('translate')('Cost'),
        template: '<span ng-bind-html="item.price | money: user.currency | trust"></span>',
        width: 115
      },
      {
        field: 'service.description',
        title: $filter('translate')('Description'),
        filter: 'localizedName',
        template: '<span title="{{::item.service.description | localizedName}}">{{::item.service.description | localizedName}}</span>'
      }
    ];
  });
