const dependencies = [
  'toaster',
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.SignupFinishedCtrl', dependencies)
  .controller('SignupFinishedCtrl', function SignupFinishedCtrl($scope, $state, userService, $filter, popupErrorService, toaster) {
    $scope.resendConfirmationEmail = function () {
      userService.sendConfirmEmail(null) // we do not have confirm_token on this page
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Email is sent!'));
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.login = function () {
      $state.go('main');
    };
  });
