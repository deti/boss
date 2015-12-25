const dependencies = [
  require('../details/details').default.name
];

export default angular.module('boss.admin.FlavorsDetailsCtrl', dependencies)
  .controller('FlavorsDetailsCtrl', function FlavorsDetailsCtrl($scope, $controller, $filter, flavor) {
    $scope.defaultState = 'flavors.details.params';
    $scope.thisState = 'flavors.details';
    if (flavor) {
      angular.extend(this, $controller('DetailsBaseCtrl', {$scope: $scope}));
    }

    $scope.tabs = [
      {link: 'flavors.details.params', title: $filter('translate')('Parameters')},
      {link: 'flavors.details.tariffs', title: $filter('translate')('Plans with this Template')}
    ];
  });
