const dependencies = [
  'toaster',
  require('../skyline.events').default.name,
  require('../../pollService/pollService').default.name
];

export default angular.module('skyline.volumes.newCtrl', dependencies)
  .controller('OSVolumesNewCtrl', function OSVolumesNewCtrl($scope, $filter, Cinder, Nova, servers, pollService, VOLUME_STATUS, $state, toaster, limits, $rootScope, SKYLINE_EVENTS) {
    $scope.servers = servers;
    $scope.volume = {};

    $scope.createVolume = function (form) {
      Cinder.createVolume($scope.volume)
        .then(function (rsp) {
          if (!$scope.volume.serverRef) {
            $rootScope.$emit(SKYLINE_EVENTS.VOLUME_CREATED);
            toaster.pop('success', $filter('translate')('Disk created'));
            $state.go('openstack.volumes', {}, {reload: true});
          } else {
            var pollPromise = pollService.startPolling(getVolumeInfo, {}, 1 * 1000, 5, checkState);
            pollPromise.catch(function (err) {
              if (err !== 'canceled') {
                toaster.pop('error', $filter('translate')('Disk is not attachable'));
                $state.go('openstack.volumes', {}, {reload: true});
              }
            });
          }

          function checkState(vol) {
            if (vol.status !== VOLUME_STATUS.creating.value) {
              pollService.stopPolling(pollPromise);

              Nova.attachVolume($scope.volume.serverRef, rsp.volume.id)
                .then(function (rsp) {
                  $rootScope.$emit(SKYLINE_EVENTS.VOLUME_CREATED);
                  toaster.pop('success', $filter('translate')('Disk created with Server'));
                  $state.go('openstack.volumes', {}, {reload: true});
                }, function (err) {
                  toaster.pop('error', $filter('translate')('Error in the servers disk creation'));
                  $state.go('openstack.volumes', {}, {reload: true});
                });
            }
          }

          function getVolumeInfo() {
            return Cinder.volume(rsp.volume.id);
          }
        }, function (err) {
          form.$resetSubmittingState();
          toaster.pop('error', $filter('translate')('Error in the disk creation'));
        });
    };

    $scope.limits = {
      volumesMax: limits.absolute.maxTotalVolumes,
      volumesUsed: limits.absolute.totalVolumesUsed + 1,
      gigabytesTotal: limits.absolute.maxTotalVolumeGigabytes,
      gigabytesUsed: limits.absolute.totalGigabytesUsed
    };

    $scope.overLimits = false;
    $scope.$watch('volume.size', function (size) {
      size = parseInt(size);
      if (!size || !_.isNumber(size)) {
        return;
      }
      $scope.limits.gigabytesUsed = limits.absolute.totalGigabytesUsed + size;
      $scope.overLimits = $scope.limits.volumesUsed > $scope.limits.volumesMax || $scope.limits.gigabytesUsed > $scope.limits.gigabytesTotal;
    });
  });
