const dependencies = [];

export default angular.module('skyline.simple.AuthorizationCtrl', dependencies)
  .controller('AuthorizationCtrl', function AuthorizationCtrl($scope, openstackAuth, $state) {
    $scope.login = '';
    $scope.password = '';
    $scope.tenantId = '';

    $scope.submit = function (form) {
      openstackAuth.auth($scope.login, $scope.password)
        .then(function (data) {
          $state.go('openstack', data);
        })
        .catch(e => {
          form.$parseErrors(e);
        });
    };
  });
