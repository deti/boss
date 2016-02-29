const dependencies = ['toaster'];

export default angular.module('skyline.dns.newCtrl', dependencies)
  .controller('OSDomainNewCtrl', function OSDomainNewCtrl($scope, $filter, $state, Designate, toaster, userInfo) {
    $scope.domain = {};
    $scope.domain.email = userInfo.email;

    $scope.createDomain = function (form) {
      if (!_.endsWith($scope.domain.name, '.')) {
        $scope.domain.name = $scope.domain.name + '.';
      }
      Designate.createDomain($scope.domain)
        .then(rsp => {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Domain was successfully created'));
          $state.go('openstack.dns.domains', {}, {reload: true});
        })
        .catch(err => {
          form.$resetSubmittingState();
          toaster.pop('error', $filter('translate')('Error on domain creation'));
          console.log('error', err);
        });
    };
  });
