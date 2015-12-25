const dependencies = [
  require('./BaseOpenstack').default.name
];

export default angular.module('boss.openstackService.Designate', dependencies)
  .factory('Designate', function (BaseOpenstack, $q) {
    class Designate extends BaseOpenstack {
      constructor() {
        super('/designate/v1/', {wrapPutRequest: false});
      }

      domains() {
        return this.Restangular.all('domains').getList()
          .then(domains => {
            var promises = domains.map(domain => {
              return this.domainRecords(domain);
            });
            return $q.all(promises);
          });
      }

      domainRecords(domain) {
        return this.records(domain.id)
          .then(recordsRsp => {
            domain.records = recordsRsp.length ? recordsRsp.length : 0;
            return domain;
          });
      }

      domain(id) {
        return this.Restangular.one('domains', id).get();
      }

      createDomain(domain) {
        return this.Restangular.one('domains').post('', {name: domain.name, email: domain.email});
      }

      deleteDomain(domain) {
        return this.Restangular.one('domains', domain.id).customDELETE();
      }

      records(domainId) {
        return this.Restangular.one('domains', domainId).all('records').getList();
      }

      record(domainId, recordId) {
        return this.Restangular.one('domains', domainId).one('records', recordId).get();
      }

      createRecord(domainId, record) {
        return this.Restangular.one('domains', domainId).one('records')
          .post('', {
            name: record.name,
            type: record.type,
            data: record.data,
            priority: record.priority ? parseInt(record.priority) : null
          });
      }

      updateRecord(domainId, record) {
        return this.Restangular.one('domains', domainId).one('records', record.id)
          .customPUT({
            name: record.name,
            type: record.type,
            data: record.data,
            priority: record.priority ? parseInt(record.priority) : null
          });
      }

      deleteRecord(record) {
        return this.Restangular.one('domains', record.domain_id).one('records', record.id).customDELETE();
      }

      constructRecordName(recordName, domainName) {
        var resultName = recordName;
        if (resultName) {
          if (!_.endsWith(resultName, '.')) {
            resultName = resultName + '.';
          }
          if (!_.endsWith(resultName, domainName)) {
            resultName = resultName + domainName;
          }
        } else {
          resultName = domainName;
        }
        return resultName;
      }

      constructRecordData(data, domainName) {
        var resultData = data;
        if (!_.endsWith(resultData, '.')) {
          resultData = resultData + '.';
        }
        if (resultData.split('.').length <= 2) {
          resultData = resultData + domainName;
        }
        return resultData;
      }
    }

    return new Designate();
  })
  .value('recordTypes', ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SRV', 'CNAME', 'DNAME']);
