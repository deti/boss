const dependencies = [
  'toaster',
  require('../../openstackService/DesignateV2').default.name
];

export default angular.module('skyline.ptr.newCtrl', dependencies)
  .controller('PTRNewCtrl', function PTRNewCtrl($scope, DesignateV2, zones, userInfo, ips, PTR_POSTFIX, $stateParams, $state, toaster, $filter) {
    if (!$stateParams.serverId) {
      $state.go('openstack.ptr');
    }
    var selectedIp = _.find(ips, ip => ip.server.id === $stateParams.serverId);
    if (!selectedIp) {
      $state.go('openstack.ptr');
    }
    $scope.ips = ips;
    $scope.zones = zones;
    $scope.zoneInfo = {
      email: userInfo.email,
      ip: selectedIp.ip,
      domain: ''
    };

    $scope.createZone = function (form) {
      if (!_.endsWith($scope.zoneInfo.domain, '.')) {
        $scope.zoneInfo.domain += '.';
      }
      var zone = {
        name: DesignateV2.ptrNameFromIp($scope.zoneInfo.ip),
        email: $scope.zoneInfo.email,
        ttl: 3600,
        description: `${PTR_POSTFIX} zone`
      };
      var recordSet = {
        name: zone.name,
        description: 'A PTR recordset',
        type: 'PTR',
        ttl: 3600,
        records: [
          $scope.zoneInfo.domain
        ]
      };

      DesignateV2.createZone(zone)
        .then(_zone => {
          zone = _zone;
          return DesignateV2.createRecordset(zone, recordSet);
        })
        .catch(e => {
          return DesignateV2.createRecordset(zone, recordSet);
        })
        .then(r => {
          $state.go('openstack.ptr', {}, {reload: true, inherit: false});
        })
        .catch(e => {
          if (e.status === 409) {
            toaster.pop('error', $filter('translate')('PTR record for this server already exist'));
          } else if (e.status === 400 && e.data.errors && e.data.errors.errors && e.data.errors.errors[0] && e.data.errors.errors[0].message) {
            toaster.pop('error', e.data.errors.errors[0].message);
          } else if (e.status < 500) {
            toaster.pop('error', $filter('translate')('Error in the request processing'));
            console.log(e);
          } else {
            toaster.pop('error', $filter('translate')('Server error'));
            console.log(e);
          }
          form.$resetSubmittingState();
        });
    };
  });
