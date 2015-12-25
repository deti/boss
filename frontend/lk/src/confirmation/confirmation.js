const dependencies = [
  'toaster',
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.confirmation', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('confirmation', {
        parent: 'boss-clean',
        url: '/confirmation/:token',
        views: {
          'main@boss-clean': {
            controller: 'ConfirmationCtrl'
          }
        },
        resolve: {
          emailConfirmation: function (userService, $stateParams, $state) {
            return userService.confirmEmail($stateParams.token)
              .then(function (rsp) {
                rsp.error = false;
                return rsp;
              }, function (e) {
                var errorObj = e.data;
                errorObj.error = true;
                return errorObj;
              });
          }
        }
      })
      .state('confirmation.main', {
        views: {
          'main@boss-clean': {
            controller: 'ConfirmationMainCtrl',
            template: require('./confirmation.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-auth',
          pageTitle: 'Confirmation'
        }
      });
  })

  .controller('ConfirmationCtrl', function (emailConfirmation, $state) {
    if ($state.is('confirmation')) {
      if (emailConfirmation.password_token) {
        $state.go('setPassword', {key: emailConfirmation.password_token});
      } else {
        $state.go('confirmation.main');
      }
    }
  })

  .controller('ConfirmationMainCtrl', function ($scope, $state, emailConfirmation, userService, $filter, $stateParams, toaster, popupErrorService) {
    $scope.error = emailConfirmation.error;

    if (emailConfirmation.error) {
      $scope.errorMsg = emailConfirmation.localized_message;
    }
    $scope.toLogin = function () {
      $state.go('main');
    };
    $scope.resendConfirmationEmail = function () {
      userService.sendConfirmEmail($stateParams.token)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Email is sent!'));
          $state.go('authorization');
        }, function (e) {
          popupErrorService.show(e);
        });
    };
  });
