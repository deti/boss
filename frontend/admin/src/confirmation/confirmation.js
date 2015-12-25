const dependencies = [];

export default angular.module('boss.admin.confirmation', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('confirmation', {
      parent: 'boss-clean',
      url: '/confirmation',
      views: {
        'main@boss-clean': {
          controller: 'ConfirmationCtrl',
          template: require('./confirmation.tpl.html')
        }
      },
      data: {
        pageTitle: 'Confirmation'
      }
    });
  })
  .controller('ConfirmationCtrl', function ($scope, $rootScope, $state) {
    console.log('Hello from ConfirmationCtrl');
    $scope.go = function (st) {
      $state.go(st);
    };
    $scope.toAdminCabinet = function () {
      $state.go('main');
    };
  });
