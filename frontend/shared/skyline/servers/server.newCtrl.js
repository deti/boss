const dependencies = [
  require('../../passwordGenerator/passwordGenerator').default.name,
  require('../skyline.events').default.name
];

export default angular.module('skyline.servers.newCtrl', dependencies)
  .value('SERVER_USE_EXTERNAL_NETWORK', true)
  .controller('OSServersNewCtrl', function OSServersNewCtrl($scope, $filter, $state, toaster, Nova, keypairs,
                                                            flavors, images, volumes, snapshots, networks, $stateParams,
                                                            passwordGenerator, limits, SERVER_USE_EXTERNAL_NETWORK,
                                                            $rootScope, SKYLINE_EVENTS) {
    var network = networks.length === 1 ? networks[0] : _.find(networks, net => {
      if (net.subnets.length === 0) {
        return false;
      }
      // if we want to ise floating ip we should create server in private network
      if (SERVER_USE_EXTERNAL_NETWORK) {
        return net['router:external'] === true;
      } else {
        return net['router:external'] === false;
      }
    });
    if (network === undefined) {
      network = _.find(network, net => net.subnets.length > 0);
    }
    if (network === undefined) {
      network = networks[0];
    }
    $scope.keypairFormVisible = false;
    $scope.authBy = 'pass';
    $scope.passwordLength = 12;
    $scope.keypairs = keypairs;
    $scope.flavors = flavors;
    $scope.snapshots = snapshots;
    $scope.volumes = volumes;
    $scope.images = images;
    $scope.server = {
      flavorRef: $stateParams.flavorRef ? $stateParams.flavorRef : (flavors.length ? flavors[0].id : null),
      key_name: keypairs.length > 0 ? keypairs[0].keypair.name : null,
      adminPass: null,
      networks: [
        {uuid: network.id}
      ],
      block_device_mapping_v2: [{
        source_type: $stateParams.source_type,
        boot_index: 0,
        delete_on_termination: false,
        volume_size: $stateParams.volume_size ? $stateParams.volume_size : null,
        destination_type: 'volume',
        uuid: null
      }]
    };
    $scope.keypair = {};
    $scope.create = function (form) {
      if (form.$invalid) {
        return;
      }
      form.$$submiting = true;
      Nova.createServer($scope.server)
        .then(function () {
          toaster.pop('success', $filter('translate')('Server was successfully created'));
          $rootScope.$emit(SKYLINE_EVENTS.SERVER_CREATED);
          $state.go('openstack.servers.list', {}, {reload: true});
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on server creation'));
          form.$resetSubmittingState();
        });
    };

    var updateVolumeSize = function (newVal) {
      var flavor = _.find(flavors, item => item.id === newVal);
      if (flavor && $scope.server.block_device_mapping_v2[0].source_type && flavor.disk !== undefined) {
        $scope.server.block_device_mapping_v2[0].volume_size = flavor.disk || 1;
      }
    };
    $scope.$watch('server.flavorRef', updateVolumeSize);

    $scope.$watch('server.block_device_mapping_v2[0].source_type', function (source) {
      switch (source) {
        case 'image':
          $scope.server.block_device_mapping_v2[0].uuid = $stateParams.imageRef || images[0].id;
          updateVolumeSize($scope.server.flavorRef);
          break;
        case 'snapshot':
          $scope.server.block_device_mapping_v2[0].uuid = $stateParams.snapshotRef || snapshots[0].id;
          break;
        case 'volume':
          $scope.server.block_device_mapping_v2[0].uuid = $stateParams.volumeRef || volumes[0].id;
      }
    });

    $scope.$watch('authBy', function (authBy) {
      if (authBy == 'key') {
        delete $scope.server.adminPass;
        $scope.server.key_name = keypairs.length > 0 ? keypairs[0].keypair.name : null;
      } else {
        delete $scope.server.key_name;
        $scope.generatePassword();
      }
    });

    $scope.addSSHKey = function (form) {
      if (form.$invalid) {
        return;
      }
      Nova.createKeypair($scope.keypair)
        .then(function (keypair) {
          $scope.keypairs.push(keypair);
          $scope.keypair = {};
          $scope.keypairFormVisible = false;
          $scope.server.key_name = keypair.keypair.name;
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on ssh key creation'));
        });
    };

    snapshots.forEach(snapshot => {
      snapshot.displayName = snapshot.getDisplayName();
    });
    volumes.forEach(volume => {
      volume.displayName = (volume.name || volume.id) + ` (${$filter('bytes')(volume.size, 'GB')})`;
    });

    $scope.generatePassword = function () {
      $scope.server.adminPass = passwordGenerator($scope.passwordLength);
    };
    $scope.generatePassword();

    $scope.setKeypairFormVisible = function (val) {
      $scope.keypairFormVisible = val;
    };

    $scope.overLimits = false;
    if (limits) {
      $scope.limits = {
        vmUsed: limits.absolute.totalInstancesUsed + 1,
        vmMax: limits.absolute.maxTotalInstances,
        cpuUsed: limits.absolute.totalCoresUsed,
        cpuMax: limits.absolute.maxTotalCores,
        ramUsed: limits.absolute.totalRAMUsed,
        ramMax: limits.absolute.maxTotalRAMSize
      };
      $scope.$watch('server.flavorRef', function (newVal) {
        var flavor = _.find(flavors, item => item.id === newVal);
        if (!flavor) {
          return;
        }
        $scope.limits.ramUsed = limits.absolute.totalRAMUsed + flavor.ram;
        $scope.limits.cpuUsed = limits.absolute.totalCoresUsed + flavor.vcpus;
        $scope.overLimits = $scope.limits.cpuUsed > $scope.limits.cpuMax || $scope.limits.ramUsed > $scope.limits.ramMax || $scope.limits.vmUsed > $scope.limits.vmMax;
      });
    }
  });
