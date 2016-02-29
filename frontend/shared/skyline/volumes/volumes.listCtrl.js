const dependencies = [
  'toaster',
  'restangular',
  require('../skyline.events').default.name,
  require('../../pollService/pollService').default.name
];

export default angular.module('skyline.volumes.listCtrl', dependencies)
  .value('volumeActionsTpl', require('./cell.actions.partial.tpl.html'))
  .controller('OSVolumesListCtrl', function OSVolumesListCtrl($scope, $filter, volumes, servers, toaster, Cinder, Nova, $state, pollService, VOLUME_STATUS, Restangular, $rootScope, SKYLINE_EVENTS, volumeActionsTpl) {
    $scope.actionsTplPath = volumeActionsTpl;
    $scope.volumes = volumes;
    $scope.servers = angular.copy(servers);
    $scope.VOLUME_STATUS = VOLUME_STATUS;
    $scope.actionForms = {};
    $scope.actionForms.change = false;
    $scope.actionForms.addDisk = false;

    $scope.actionHandler = function ($event, currentKey, keepActiveItem) {
      $event.stopPropagation();
      $scope.actionForms[currentKey] = !$scope.actionForms[currentKey];

      _.forEach($scope.actionForms, (value, key) => {
        if (key !== currentKey) {
          $scope.actionForms[key] = false;
        }
      });

      keepActiveItem.value = _.any($scope.actionForms);
    };

    _.filter(volumes, item => item.status.progress)
      .forEach(pollVolume);

    function pollVolume(volume) {
      var promise = pollService
        .asyncTask(() => {
          return Cinder.volume(volume.id);
        }, serverRsp => {
          if (serverRsp.status.value !== volume.status) {
            Restangular.sync(serverRsp, volume);
            volume.status = serverRsp.status;
          }
          return !serverRsp.status.progress;
        });
      promise
        .then(serverRsp => {
          return Cinder.volumeLinkedServer(serverRsp);
        })
        .then(serverRsp => {
          Restangular.sync(serverRsp, volume);
          if (serverRsp.attachments.length === 0) {
            volume.attachments = [];
          }
          volume.status = serverRsp.status;
        })
        .catch(e => {
          if (e.status === 404) {
            $rootScope.$emit(SKYLINE_EVENTS.VOLUME_DELETED);
            _.remove(volumes, volume);
          }
        });
      $scope.$on('$destroy', promise.stop);
    }

    $scope.extendVolume = function (volume) {
      $scope.actionForms.change = false;
      Cinder.extendVolume(volume)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Disk extended'));
          $rootScope.$emit(SKYLINE_EVENTS.VOLUME_EXTENDED);
          volume.size = volume.newSize;
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on disk extension'));
        });
    };

    $scope.removeVolume = function (volume) {
      volume.remove()
        .then(function () {
          pollVolume(volume);
          volume.status = angular.copy(VOLUME_STATUS.deleting);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.detachVolume = function (volume) {
      Nova.detachVolume(volume.attachments[0].server_id, volume.attachments[0].volume_id)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Disk removed'));
          volume.status.progress = true;
          pollVolume(volume);
        });
    };

    $scope.addDisk = function (volume) {
      $scope.actionForms.addDisk = false;
      Nova.attachVolume(volume.newServer, volume.id)
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Disk attached'));
          volume.status.progress = true;
          pollVolume(volume);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on disk mounting'));
        });
    };

    $scope.createImage = function (volume) {
      $scope.actionForms.image = false;
      volume.createImage(volume.imageName)
        .then(rsp => {
          toaster.pop('success', $filter('translate')('The image was successfully uploaded'));
          delete volume.imageName;
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on image creation'));
        });
    };

    $scope.columns = [
      {
        field: 'name',
        title: $filter('translate')('Name'),
        value: function (item) {
          return (item.name ? item.name : item.id);
        }
      },
      {
        field: 'size',
        title: $filter('translate')('Size'),
        template: '{{item.size}} GB'
      },
      {
        field: 'server.name',
        title: $filter('translate')('Virtual server'),
        template: '{{item.server.name}}<span ng-if="item.attachments[0]">, {{item.attachments[0].device}}</span>'
      },
      {
        field: 'status.title',
        title: $filter('translate')('Status'),
        template: '{{item.status.title|translate}}<span ng-if="item.status.progress">...</span>'
      }
    ];
  });
