const dependencies = [
  'toaster',
  require('../skyline.events').default.name
];

export default angular.module('skyline.ips.newCtrl', dependencies)
  .controller('OSIPsNewCtrl', function OSIPsNewCtrl($scope, $filter, $state, floatingIPPools, Nova, toaster, $stateParams, $location, limits, $rootScope, SKYLINE_EVENTS) {
    limits.absolute.totalFloatingIpsUsed += 1;
    $scope.limits = limits;
    $scope.floatingIPPools = floatingIPPools.plain();
    $scope.ip = {};
    $scope.ip.pool = $scope.floatingIPPools.length ? $scope.floatingIPPools[0].name : null;

    $scope.allocateFloatingIP = function (form) {
      Nova.allocateFloatingIP($scope.ip.pool)
        .then(function (rsp) {
          form.$resetSubmittingState();
          $rootScope.$emit(SKYLINE_EVENTS.IP_CREATED);
          toaster.pop('success', $filter('translate')('Floating IP requested'));
          if ($stateParams.returnUrl) {
            $location.path($stateParams.returnUrl);
          } else {
            $state.go('openstack.ips', {}, {reload: true});
          }
        })
        .catch(function (err) {
          form.$resetSubmittingState();
          toaster.pop('error', $filter('translate')('Floating IP request error'));
        });
    };

    $scope.overLimits = limits.absolute.totalFloatingIpsUsed > limits.absolute.maxTotalFloatingIps;
  });
