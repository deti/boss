const dependencies = [
  'ui.router',
  'toaster',
  require('../../lib/payService/payService').default.name,
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.Production2Ctrl', dependencies)
  .controller('Production2Ctrl', function Production2Ctrl($scope, $filter, $state, toaster, payService, userService, userInfo) {
    $scope.saveAsDefault = true;
    $scope.userInfo = userInfo;
    $scope.amount = 10;

    $scope.payPrivate = function () {
      payService.payOnce($scope.amount, userInfo, $scope.saveAsDefault)
        .then(function () {
          return userService.userInfo(true);
        })
        .then(function (updatedUserInfo) {
          toaster.pop('success', $filter('translate')('The payment was successful'));
          angular.copy(updatedUserInfo, userInfo);
          $state.go('main');
        })
        .catch(function (e) {
          toaster.pop('error', e.reason);
        });
    };
    $scope.downloadInvoice = function (form) {
      userService.downloadInvoice($scope.amount)
        .then(function () {
          form.$resetSubmittingState();
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
    $scope.finish = function () {
      $state.go('main');
    };
  });
