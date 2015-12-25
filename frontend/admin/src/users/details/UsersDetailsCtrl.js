const dependencies = [
  'ui.router',
  'toaster',
  'restangular',
  require('../../../lib/userService/userService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];

const rulesTplPath = require('../roles.partial.tpl.html');

export default angular.module('boss.admin.UsersDetailsCtrl', dependencies)
  .controller('UsersDetailsCtrl', function UsersDetailsCtrl($scope, $state, $filter, toaster, Restangular, userService, popupErrorService, userInfo, user, userRoles) {
    $scope.rulesTplPath = rulesTplPath;
    $scope.user = Restangular.copy(user);
    $scope.roles = userRoles;

    $scope.update = function (form) {
      $scope.user.save()
        .then(function (updatedUser) {
          Restangular.sync(updatedUser, $scope.user);
          Restangular.sync(updatedUser, user);
          toaster.pop('success', $filter('translate')('User account is successfully changed'));
        }).catch(function (rsp) {
        form.$parseErrors(rsp);
      });
    };

    $scope.archiveUser = function () {
      var promise, currentUser;

      currentUser = ($scope.user.user_id === userInfo.user_id);
      if (currentUser) {
        promise = userService.archiveMe();
      } else {
        promise = userService.archiveUser($scope.user);
      }

      promise.then(function () {
        toaster.pop('success', currentUser ? $filter('translate')('User account is deleted') : $filter('translate')('User account is deleted'));
        $state.go('users', {}, {reload: true});
      }, function (err) {
        popupErrorService.show(err);
      });
    };
  });
