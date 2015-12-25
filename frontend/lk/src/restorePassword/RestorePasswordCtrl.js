const dependencies = [
  'ui.router',
  require('../../lib/userService/userService').default.name,
  require('../../../shared/bsServerValidate/bsServerValidate').default.name,
  require('../../../shared/bsFormSendOnce/bsFormSendOnce').default.name
];

export default angular.module('boss.lk.RestorePasswordCtrl', dependencies)
  .controller('RestorePasswordCtrl', function RestorePasswordCtrl($scope, userService, $state) {
    $scope.email = '';
    $scope.restorePassword = function (form) {
      userService.resetPassword($scope.email)
        .then(function () {
          form.$resetSubmittingState();
          $state.go('restorePasswordComplete');
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
