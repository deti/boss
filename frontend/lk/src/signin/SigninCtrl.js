const dependencies = [
  'ui.router',
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.SigninCtrl', dependencies)
  .controller('SigninCtrl', function SigninCtrl($scope, userService, $state, $stateParams) {
    $scope.submit = function (form) {
      userService.auth($scope.email, $scope.password)
        .then(function () {
          form.$resetSubmittingState();
          if ($stateParams.returnState) {
            $state.go($stateParams.returnState, $stateParams.returnParams);
          } else {
            $state.go('main');
          }
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
