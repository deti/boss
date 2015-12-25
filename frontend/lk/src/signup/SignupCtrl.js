const dependencies = [
  'toaster',
  'vcRecaptcha',
  require('../../lib/userService/userService').default.name
];

import 'angular-recaptcha/release/angular-recaptcha';

export default angular.module('boss.lk.SignupCtrl', dependencies)
  .controller('SignupCtrl', function SignupCtrl($scope, $rootScope, $state, $stateParams, userService, vcRecaptchaService, $filter, toaster, CONST, $window) {
    $scope.offer_link = CONST.local.offer_link;
    $scope.promo_registration_only = CONST.local.promo_registration_only;
    $scope.user = {};
    if ($stateParams.promo) {
      $scope.user.promo_code = $stateParams.promo;
    }

    $scope.checkboxes = {
      offer: false,
      processing: false
    };
    $scope.register = function (form) {
      var user = _.clone($scope.user);
      var recaptchaRsp;
      try {
        recaptchaRsp = vcRecaptchaService.getResponse();
      } catch (ex) {
        vcRecaptchaService.reload();
        toaster.pop('error', $filter('translate')('Could not verify that you are not a robot. Try again.'));
        return;
      }

      userService.signup(user, recaptchaRsp)
        .then(function (rsp) {
          form.$resetSubmittingState();
          $state.go('signupFinished', {user: rsp});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
    $scope.openOffer = function () {
      $window.open($scope.offer_link, '_blank', 'toolbar=0,location=0,menubar=0');
    };
  });
