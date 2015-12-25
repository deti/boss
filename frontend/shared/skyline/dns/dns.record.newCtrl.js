const dependencies = ['toaster', 'ui.router'];

export default angular.module('skyline.dns.record.newCtrl', dependencies)
  .controller('OSRecordNewCtrl', function OSRecordNewCtrl($scope, domain, $filter, $state, Designate, recordTypes, toaster) {
    $scope.record = {};
    $scope.domain = domain;
    $scope.recordTypes = recordTypes;

    $scope.createRecord = function (form) {
      $scope.record.name = Designate.constructRecordName($scope.record.name, $scope.domain.name);
      if ($scope.record.type === 'MX' || $scope.record.type === 'CNAME' || $scope.record.type === 'NS') {
        $scope.record.data = Designate.constructRecordData($scope.record.data, $scope.domain.name);
      }

      Designate.createRecord($scope.domain.id, $scope.record)
        .then((rsp) => {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Subdomain was successfully created'));
          $state.go('openstack.dns.records', {domainId: $scope.domain.id}, {reload: true});
        })
        .catch((err) => {
          toaster.pop('error', $filter('translate')('Error on subdomain creation'));
          form.$resetSubmittingState();
          console.log('error', err);
        });
    };
  });
