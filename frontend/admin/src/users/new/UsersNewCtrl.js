import '../../../lib/userService/userService';

const rulesTplPath = require('../roles.partial.tpl.html');

export default angular.module('boss.admin.UsersNewCtrl', ['ui.router', 'toaster', 'boss.userService'])
  .controller('UsersNewCtrl', function UsersNewCtrl($scope, $state, $filter, userRoles, userService, toaster, usersData) {
    $scope.rulesTplPath = rulesTplPath;
    $scope.roles = userRoles;
    $scope.user = {};

    $scope.cancel = function () {
      $state.go('users');
    };
    $scope.create = function (form) {
      userService.create($scope.user)
        .then(function (user) {
          form.$resetSubmittingState();
          usersData.push(user);
          toaster.pop('success', $filter('translate')('User account is successfully created'));
          $state.go('users');
        }, function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
