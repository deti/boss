const dependencies = [
  'toaster',
  require('../../pollService/pollService').default.name,
  require('../skyline.events').default.name
];

export default angular.module('skyline.servers.editCtrl', dependencies)
  .controller('OSServersEditCtrl', function OSServersEditCtrl($scope, $filter, toaster, server, flavors, volumes,
                                                              Nova, Cinder, availableVolumes, ips, $q, pollService,
                                                              $state, $rootScope, SKYLINE_EVENTS) {
    // type and name
    $scope.server = server;
    $scope.serverFlavor = {
      flavorRef: server.flavor.id
    };
    $scope.flavors = flavors;
    $scope.saveNameAndType = function (form) {
      if (form.$invalid) {
        return;
      }
      var promises = [];
      if ($scope.serverFlavor.flavorRef !== server.flavor.id) {
        promises.push(
          server.resize($scope.serverFlavor.flavorRef)
        );
      }
      promises.push(server.save());
      $q.all(promises)
        .then(function () {
          form.$resetSubmittingState();
          $rootScope.$emit(SKYLINE_EVENTS.SERVER_UPDATED);
          toaster.pop('success', $filter('translate')('Changes are saved'));
        })
        .catch(function () {
          toaster.pop('error', $filter('translate')('Error on applying changes'));
          form.$resetSubmittingState();
        });
    };

    // volumes
    var transformAttachedVolume = volume => {
      volume.attachment = _.find(volume.attachments, attach => attach.server_id === server.id);
      return volume;
    };
    var transformAvailableVolume = volume => {
      volume.about = volume.name ? volume.name : volume.id;
      volume.about += ` (${volume.size} GB)`;
      return volume;
    };
    volumes.forEach(transformAttachedVolume);
    availableVolumes.forEach(transformAvailableVolume);
    $scope.volumes = volumes;
    $scope.availableVolumes = availableVolumes;

    $scope.attachVolume = function (volume) {
      if (!volume) {
        return;
      }
      Nova.attachVolume(server.id, volume.id)
        .then(() => {
          var index = _.findIndex(availableVolumes, v => v.id === volume.id);
          availableVolumes.splice(index, 1);
          volumes.push(transformAttachedVolume(volume));
        })
        .then(() => {
          return pollService.asyncTask(function () {
            return Cinder.volume(volume.id);
          }, volumeData => {
            return volumeData.status.value === 'in-use';
          });
        })
        .then(volumeUpdated => {
          var index = _.findIndex(volumes, v => v.id === volumeUpdated.id);
          volumes[index] = transformAttachedVolume(volumeUpdated);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on disk mount'));
        });
    };

    $scope.detach = function (volume) {
      Nova.detachVolume(server.id, volume.id)
        .then(() => {
          toaster.pop('success', $filter('translate')('Disk removed'));
          var index = _.findIndex(volumes, volume);
          volumes.splice(index, 1);
          availableVolumes.push(transformAvailableVolume(volume));
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on disk unmounting'));
        });
    };

    // IP
    $scope.ips = ips;
    var serverFloatingAddress = _.find(ips, ip => ip.instance_id === server.id),
      serverStaticAddress = _.find(server.ips, i => i['OS-EXT-IPS:type'] === 'fixed');
    $scope.ip = {
      serverFloatingAddress: serverFloatingAddress ? serverFloatingAddress.ip : null,
      serverStaticAddress: serverStaticAddress ? serverStaticAddress.addr : null
    };
    $scope.pageHref = $state.href($state.$current.name, {id: server.id});

    $scope.saveIP = function (form) {
      if (form.$invalid) {
        return;
      }
      if ($scope.ip.serverFloatingAddress !== serverFloatingAddress) {
        var promise;
        if (serverFloatingAddress !== undefined) { // remove ip from server if it already attached
          promise = Nova.removeFloatIPFromServer(serverFloatingAddress);
        } else {
          promise = $q.when(true);
        }
        promise
          .then(function () {
            return server.addIp($scope.ip.serverFloatingAddress);
          })
          .then(function () {
            form.$resetSubmittingState();
            toaster.pop('success', $filter('translate')('Address assigned'));
          })
          .catch(function () {
            toaster.pop('error', $filter('translate')('Error on address assignment'));
            form.$resetSubmittingState();
          });
      }
    };
  });
