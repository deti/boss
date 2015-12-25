const dependencies = [
  'toaster',
  require('../../lib/utilityService/utilityService').default.name,
  require('../../../shared/localStorage/localStorage').default.name
];

export default angular.module('boss.admin.SystemCtrl', dependencies)
  .controller('SystemCtrl', function SystemCtrl($scope, utilityService, toaster, $filter, localStorage) {
    $scope.sendTo = localStorage.getItem('test_email_send_to', '');
    $scope.sendCC = localStorage.getItem('test_email_send_cc', []);
    $scope.subject = localStorage.getItem('test_email_subject', '');

    $scope.sendEmail = function (form) {
      var sendCC = $scope.sendCC.map(item => item.text);
      utilityService.testEmail($scope.sendTo, sendCC, $scope.subject)
        .then(function () {
          localStorage.setItem('test_email_send_to', $scope.sendTo);
          localStorage.setItem('test_email_send_cc', $scope.sendCC);
          localStorage.setItem('test_email_subject', $scope.subject);
          toaster.pop('success', $filter('translate')('Test message is sent'));
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
