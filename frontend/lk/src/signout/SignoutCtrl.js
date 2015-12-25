const dependencies = [
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.SignoutCtrl', dependencies)
  .controller('SignoutCtrl', function SignoutCtrl($scope, userService, $state) {
    userService.logout()
      .then(function () {
        $state.go('signin');
      });
  });
