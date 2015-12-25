const dependencies = [
  require('./BaseOpenstack').default.name
];

export default angular.module('boss.openstackService.DesignateV2', dependencies)
  .factory('DesignateV2', function (BaseOpenstack, $q, PTR_POSTFIX) {
    class DesignateV2 extends BaseOpenstack {
      constructor() {
        super('/designate/v2/', {wrapPutRequest: false});

        this.Restangular.addRequestInterceptor(function (elem, operation, what) {
          if (what === 'recordsets' && operation === 'put') {
            return {
              records: elem.records
            };
          }
          return elem;
        });
      }

      static ptrNameFromIp(ip) {
        return ip.split('.').reverse().join('.') + PTR_POSTFIX;
      }

      static ipFromPtrName(name) {
        name = name.replace(PTR_POSTFIX, '');
        return name.split('.').reverse().join('.');
      }

      zones() {
        return this.Restangular.all('zones').getList();
      }

      zone(id) {
        return this.Restangular.one('zones', id).get();
      }

      zonesRecordsets(zones) {
        var promises = zones.map(zone => {
          return this.zoneRecordsets(zone)
            .then(recordset => {
              zone.recordset = recordset;
              return zone;
            });
        });
        return $q.all(promises);
      }

      filterPtrZones(zones) {
        return _.filter(zones, zone => _.endsWith(zone.name, PTR_POSTFIX));
      }

      filterNotPtrZones(zones) {
        return _.filter(zones, zone => !_.endsWith(zone.name, PTR_POSTFIX));
      }

      createZone(zone) {
        return this.Restangular.all('zones').post(zone);
      }

      zoneRecordsets(zone) {
        return this.Restangular.one('zones', zone.id).all('recordsets').getList();
      }

      createRecordset(zone, recordSet) {
        return this.Restangular.one('zones', zone.id).all('recordsets').post(recordSet);
      }
    }

    return new DesignateV2();
  })
  .constant('PTR_POSTFIX', '.in-addr.arpa.');
