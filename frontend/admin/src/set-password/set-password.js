const dependencies = [
  require('../../lib/currentUserService/currentUserService').default.name
];

export default angular.module('boss.admin.setPassword', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('setPassword', {
      parent: 'boss-clean',
      url: '/set-password/:token',
      views: {
        'main@boss-clean': {
          controller: 'SetPasswordCtrl',
          template: require('./set-password.tpl.html')
        }
      },
      data: {
        pageTitle: 'Password restoration',
        bodyClassname: 'body-gray auth-view'
      },
      resolve: {
        isValid: function (currentUserService, $stateParams) {
          return currentUserService.resetPasswordIsValid($stateParams.token);
        }
      }
    });
  })
  .controller('SetPasswordCtrl', function ($scope, isValid, currentUserService, $state, $stateParams) {
    $scope.isValid = isValid;
    $scope.submit = function (form) {
      currentUserService.setPassword($scope.password, $stateParams.token)
        .then(function () {
          $state.go('signin');
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
