const dependencies = [];

export default angular.module('boss.admin.FlavorsCtrl', dependencies)
  .controller('FlavorsCtrl', function FlavorsCtrl($scope, $filter, flavors) {
    $scope.pages = Math.ceil(parseInt(flavors.total) / parseInt(flavors.perPage));
    $scope.flavors = flavors;
    $scope.columns = [
      {
        title: $filter('translate')('Name'),
        filter: 'localizedName'
      },
      {
        field: 'flavor.flavor_id',
        title: $filter('translate')('Flavor ID')
      },
      {
        field: 'flavor.disk',
        title: $filter('translate')('HDD'),
        filter: {name: 'bytes', args: ['gb']},
        width: 140
      },
      {
        field: 'flavor.ram',
        title: $filter('translate')('RAM'),
        filter: {name: 'bytes', args: ['mb']},
        width: 140
      },
      {
        field: 'flavor.vcpus.toString()',
        title: $filter('translate')('vCPU'),
        width: 100
      },
      {
        title: $filter('translate')('Changeable'),
        value: function (item) {
          return item.mutable ? $filter('translate')('Yes') : $filter('translate')('No');
        },
        width: 140
      }
    ];
    $scope.searchTags = [];
    $scope.filters = [
      {
        property: 'visibility', title: $filter('translate')('Status'), options: [
        {text: $filter('translate')('Active'), val: 'visible'},
        {text: $filter('translate')('In archive'), val: 'deleted'}
      ]
      }
    ];
  });
