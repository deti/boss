const dependencies = [
  require('../../openstackService/DesignateV2').default.name
];

export default angular.module('skyline.ptr.listCtrl', dependencies)
  .value('ptrActionsTpl', require('./cell.actions.partial.tpl.html'))
  .controller('PTRListCtrl', function PTRListCtrl($scope, zones, ips, $filter, DesignateV2, ptrActionsTpl, toaster) {
    $scope.actionsTplPath = ptrActionsTpl;
    ips = _.clone(ips, true);
    zones = _.clone(zones, true);
    const emptyZoneRecord = {
      name: '-',
      recordset: {
        records: ['-']
      }
    };
    ips.forEach(ip => {
      const reverseName = DesignateV2.ptrNameFromIp(ip.ip);
      ip.zone = _.find(zones, {name: reverseName});

      if (ip.zone) {
        _.remove(zones, ip.zone);
        ip.zone.recordset = _.find(ip.zone.recordset, {type: 'PTR'});
      } else {
        ip.zone = emptyZoneRecord;
      }
    });
    if (zones.length > 0) { // there are zones without real server
      zones.forEach(zone => {
        zone.recordset = _.find(zone.recordset, {type: 'PTR'});
        ips.push({
          zone,
          ip: '-',
          server: {
            name: '-'
          }
        });
      });
    }
    $scope.ips = ips;

    $scope.removePtr = function (ip) {
      ip.zone.remove()
        .then(() => {
          if (ip.server.id) {
            ip.zone = emptyZoneRecord;
          } else {
            _.remove(ips, ip);
          }
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.columns = [
      {
        field: 'ip',
        title: $filter('translate')('IP-address')
      },
      {
        field: 'server.name',
        title: $filter('translate')('Virtual server')
      },
      {
        field: 'zone.recordset.records[0]',
        title: $filter('translate')('Domain')
      }
    ];
  });
