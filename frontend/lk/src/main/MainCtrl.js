const dependencies = [
  require('../../lib/userService/userService').default.name,
  require('../../../shared/pollService/pollService').default.name
];

export default angular.module('boss.lk.MainCtrl', dependencies)
  .controller('MainCtrl', function ($scope, $filter, userService, pollService, userInfo, tariff, period, quotas) {
    $scope.user = userInfo;
    $scope.tariff = tariff;
    $scope.groupsOfQuotas = quotas;
    $scope.period = period;
    $scope.showState = true;

    if (quotas.loading) {
      var task = pollService.asyncTask(userService.usedQuotas, quotasRsp => !quotasRsp.loading);
      task
        .then(quotasRsp => {
          angular.copy(quotasRsp, quotas);
          pollQuotas();
        });
      $scope.$on('$destroy', task.stop);
    } else {
      pollQuotas();
    }
    function pollQuotas() {
      var pollId = pollService.startPolling(userService.usedQuotas, quotas, 5 * 60 * 1000);
      $scope.$on('$destroy', pollId.stop);
    }
  });
