const dependencies = [
  'ui.router',
  require('../../lib/currentUserService/currentUserService').default.name
];

export default angular.module('boss.admin.SigninCtrl', dependencies)
  .controller('SigninCtrl', function ($scope, currentUserService, $state, $stateParams) {
    $scope.submit = function (form) {
      currentUserService.auth($scope.login, $scope.password)
        .then(function () {
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
