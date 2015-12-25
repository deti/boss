const dependencies = ['toaster'];

export default angular.module('skyline.dns.recordsCtrl', dependencies)
  .value('dnsRecordsActionsTpl', require('./cell.record.actions.partial.tpl.html'))
  .controller('OSRecordsCtrl', function OSRecordsCtrl($scope, domain, records, Designate, $filter, toaster, dnsRecordsActionsTpl) {
    $scope.actionsTplPath = dnsRecordsActionsTpl;
    $scope.domain = domain;
    $scope.records = records;

    $scope.deleteRecord = function (record) {
      Designate.deleteRecord(record)
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Subdomain was successfully deleted'));
          var index = _.findIndex($scope.records, record);
          records.splice(index, 1);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.columns = [
      {
        field: 'name',
        title: $filter('translate')('Name')
      },
      {
        field: 'type',
        title: $filter('translate')('Type')
      },
      {
        field: 'data',
        title: $filter('translate')('Record')
      }
    ];
  });
