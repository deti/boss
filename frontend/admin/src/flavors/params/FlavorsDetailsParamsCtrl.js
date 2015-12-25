const dependencies = [
  'ui.router',
  'toaster',
  'restangular',
  require('../../../lib/serviceService/serviceService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];

export default angular.module('boss.admin.FlavorsDetailsParamsCtrl', dependencies)
  .controller('FlavorsDetailsParamsCtrl', function FlavorsDetailsParamsCtrl($scope, $filter, $state, toaster, Restangular, serviceService, popupErrorService, flavor) {
    $scope.flavor = Restangular.copy(flavor);

    $scope.save = function (form) {
      serviceService.editFlavor($scope.flavor)
        .then(function (updatedFlavor) {
          toaster.pop('success', $filter('translate')('Template is successfully updated'));
          $state.reload();
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.remove = function () {
      serviceService.remove($scope.flavor)
        .then(function () {
          toaster.pop('success', $filter('translate')('Template is successfully deleted'));
          $state.go('flavors', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.activate = function () {
      serviceService.makeImmutable($scope.flavor.service_id)
        .then(function () {
          toaster.pop('success', $filter('translate')('Template is successfully updated'));
          $state.reload();
        }, function (err) {
          popupErrorService.show(err);
        });
    };
  });
