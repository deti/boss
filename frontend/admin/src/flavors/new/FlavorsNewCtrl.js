const dependencies = [
  'ui.router',
  'toaster',
  require('../../../lib/serviceService/serviceService').default.name
];

export default angular.module('boss.admin.FlavorsNewCtrl', dependencies)
  .controller('FlavorsNewCtrl', function FlavorsNewCtrl($scope, serviceService, toaster, $filter, $state, measures) {
    $scope.flavor = {};
    $scope.measures = measures;
    $scope.create = function (form) {
      serviceService.createFlavor($scope.flavor)
        .then(function () {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Template is successfully created'));
          $state.go('flavors', {}, {reload: true});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
    $scope.cancel = function () {
      $state.go('flavors');
    };
  });
