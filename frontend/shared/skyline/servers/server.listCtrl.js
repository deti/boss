const dependencies = [
  'mgcrea.ngStrap.tooltip',
  'restangular',
  'toaster',
  require('../../pollService/pollService').default.name,
  require('../skyline.events').default.name
];

export default angular.module('skyline.servers.listCtrl', dependencies)
  .value('serverActionsTpl', require('./cell.actions.partial.tpl.html'))
  .value('serverAddressesCellTpl', require('./cell.addresses.partial.tpl.html'))
  .controller('OSServersListCtrl', function OSServersListCtrl($scope, $filter, servers, toaster, pollService, Glance, Nova, SERVER_STATUS, $state, Restangular, $rootScope, SKYLINE_EVENTS, serverActionsTpl, serverAddressesCellTpl) {
    $scope.actionsTplPath = serverActionsTpl;
    $scope.adressesTplPath = serverAddressesCellTpl;
    servers = servers.map(transformServer);
    $scope.servers = servers;
    $scope.SERVER_STATUS = SERVER_STATUS;

    $scope.serverAction = function (action, server) {
      server[action]()
        .then(() => {
          if (!server.status.progress) {
            return;
          }
          pollServer(server);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('An error occurred while processing request'));
        });
    };

    $scope.removeServer = function (server) {
      server.remove()
        .then(function () {
          server.status = angular.copy(SERVER_STATUS.DELETING);
          pollServer(server);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.clone = function (server) {
      var imageName = `${server.name}.image.${Date.now()}`;
      server.createImage(imageName)
        .then(function () {
          return Glance.images();
        })
        .then(function (images) {
          var image = _.find(images, img => img.name === imageName);
          $state.go('openstack.servers.new', {
            imageRef: image.id,
            flavorRef: server.flavor.id,
            volume_size: server.volumes[0].size
          });
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on copy process'));
        });
    };

    _.filter(servers, item => item.status.progress || !!item['OS-EXT-STS:task_state'])
      .forEach(pollServer);

    $scope.columns = [
      {
        field: 'name',
        title: $filter('translate')('Name')
      },
      {
        field: 'flavor.vcpus.toString()',
        title: 'CPU',
        width: 80
      },
      {
        field: 'flavor.ram.toString()',
        title: 'RAM',
        template: '{{::item.flavor.ram}} MB',
        width: 120
      },
      {
        field: 'volumeSize',
        title: $filter('translate')('Disk size'),
        filter: {name: 'bytes', args: ['GB']},
        width: 165
      },
      {
        field: 'imageName',
        title: $filter('translate')('Image')
      },
      {
        field: 'addresses.ips.length',
        title: $filter('translate')('Address'),
        cellClass: 'long-text',
        templateUrl: serverAddressesCellTpl
      },
      {
        field: 'status.title',
        title: $filter('translate')('Status'),
        template: '{{item.status.title | translate}}<span ng-if="item.status.progress">...</span>'
      }
    ];

    function pollServer(server) {
      var promise = pollService
        .asyncTask(() => {
          return Nova.server(server.id);
        }, serverRsp => {
          if (serverRsp.status.value !== server.status) {
            Restangular.sync(serverRsp, server);
            server.status = serverRsp.status;
          }
          return !serverRsp['OS-EXT-STS:task_state'] && !serverRsp.status.progress;
        });
      promise
        .then(serverRsp => {
          return Nova.serverLinkedData(serverRsp);
        })
        .then(transformServer)
        .then(serverRsp => {
          Restangular.sync(serverRsp, server);
          server.status = serverRsp.status;
        })
        .catch(e => {
          if (e.status === 404) {
            $rootScope.$emit(SKYLINE_EVENTS.SERVER_DELETED);
            _.remove(servers, server);
          }
        });
      $scope.$on('$destroy', promise.stop);
    }

    function transformServer(server) {
      if (server.volumes && server.volumes.length) {
        var value = _.reduce(server.volumes, (total, volume) => total + volume.size, 0);
        server.volumeSize = value.toString();
      } else {
        server.volumeSize = '-';
      }

      if (server.volumes && server.volumes[0] && server.volumes[0].volume_image_metadata && server.volumes[0].volume_image_metadata.image_name) {
        // server with volume created from image
        server.imageName = server.volumes[0].volume_image_metadata.image_name;
      } else {
        server.imageName = server.image.name ? server.image.name : '-';
      }

      return server;
    }
  });
