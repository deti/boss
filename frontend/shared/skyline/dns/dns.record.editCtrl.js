const dependencies = ['toaster', 'ui.router'];

export default angular.module('skyline.dns.record.editCtrl', dependencies)
  .controller('OSRecordEditCtrl', function OSRecordEditCtrl($scope, domain, record, $filter, $state, Designate, toaster) {
    $scope.record = record;
    $scope.domain = domain;

    $scope.updateRecord = function (form) {
      $scope.record.name = Designate.constructRecordName($scope.record.name, $scope.domain.name);
      if ($scope.record.type === 'MX' || $scope.record.type === 'CNAME' || $scope.record.type === 'NS') {
        $scope.record.data = Designate.constructRecordData($scope.record.data, $scope.domain.name);
      }

      Designate.updateRecord($scope.domain.id, $scope.record)
        .then(rsp => {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Subdomain was successfully updated'));
          $state.go('openstack.dns.records', {domainId: $scope.domain.id}, {reload: true});
        })
        .catch(err => {
          toaster.pop('error', $filter('translate')('Error on applying changes'));
          form.$resetSubmittingState();
          console.log('error', err);
        });
    };
  });
