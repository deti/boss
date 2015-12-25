const dependencies = [
  require('../../lib/currentUserService/currentUserService').default.name
];

export default angular.module('boss.admin.restorePassword', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('restorePassword', {
        parent: 'boss-clean',
        url: '/restore',
        views: {
          'main@boss-clean': {
            controller: 'RestorePasswordCtrl',
            template: require('./restorePassword.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-gray',
          pageTitle: 'Password restoration'
        }
      })
      .state('restorePasswordComplete', {
        parent: 'boss-clean',
        url: '/restore-complete',
        views: {
          'main@boss-clean': {
            template: require('./restorePasswordComplete.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-gray'
        }
      });
  })
  .controller('RestorePasswordCtrl', function ($scope, currentUserService, $state) {
    $scope.email = '';
    $scope.restorePassword = function (form) {
      currentUserService.resetPassword($scope.email)
        .then(function () {
          $state.go('restorePasswordComplete');
        })
        .catch(function (rsp) {
          console.log('fail');
          console.log(rsp);
          form.$parseErrors(rsp);
        });
    };
  });
