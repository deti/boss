const dependencies = [
  'toaster',
  require('../skyline.events').default.name
];

export default angular.module('skyline.ips.listCtrl', dependencies)
  .value('ipActionsTpl', require('./cell.actions.partial.tpl.html'))
  .controller('OSIPsCtrl', function OSIPsCtrl($scope, $state, $filter, floatingIPs, servers, Nova, toaster, $rootScope, SKYLINE_EVENTS, ipActionsTpl) {
    $scope.floatingIPs = floatingIPs;
    $scope.servers = angular.copy(servers);
    $scope.actionForms = {};
    $scope.actionForms.assignIP = false;
    $scope.actionsTplPath = ipActionsTpl;

    function reduceServersList() {
      $scope.floatingIPs.forEach(function (ip, index) {
        if (ip.instance_id) {
          _.remove($scope.servers, 'id', ip.instance_id);
        }
      });
    }

    function addFreedServer(serverId) {
      var server = _.find(servers, 'id', serverId);
      $scope.servers.push(server);
    }

    reduceServersList();

    $scope.deallocateFloatingIP = function (ip) {
      Nova.deallocateFloatingIP(ip)
        .then(function (rsp) {
          $rootScope.$emit(SKYLINE_EVENTS.IP_DELETED);
          toaster.pop('success', $filter('translate')('Delete floating IP'));
          if (ip.instance_id) {
            addFreedServer(ip.instance_id);
          }
          var index = _.findIndex($scope.floatingIPs, ip);
          floatingIPs.splice(index, 1);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.removeFloatIPFromServer = function (ip) {
      Nova.removeFloatIPFromServer(ip)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Unassign floating IP'));
          if (ip.instance_id) {
            addFreedServer(ip.instance_id);
          }
          ip.newServer = null;
          ip.server = null;
          ip.instance_id = null;
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error'));
        });
    };

    $scope.assignIP = function (ip) {
      var server = _.find($scope.servers, 'id', ip.newServer);
      server.addIp(ip.ip)
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Address assigned'));
          ip.server = server.name;
          ip.instance_id = server.id;
          $scope.actionForms.assignIP = false;
          reduceServersList();
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on address assignment'));
        });
    };

    $scope.columns = [
      {
        field: 'ip',
        title: $filter('translate')('IP-address')
      },
      {
        field: 'server',
        title: $filter('translate')('Virtual server')
      }
    ];
  });
