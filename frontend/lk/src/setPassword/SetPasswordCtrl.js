const dependencies = [
  'ui.router',
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.SetPasswordCtrl', dependencies)
  .controller('SetPasswordCtrl', function SetPasswordCtrl($scope, $stateParams, $state, userService, isValid) {
    $scope.isValid = isValid;
    $scope.password = '';
    $scope.restorePassword = function (form) {
      userService.setPassword($stateParams.key, $scope.password)
        .then(function () {
          form.$resetSubmittingState();
          $state.go('signin');
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
