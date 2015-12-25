const dependencies = [
  'ui.router',
  'toaster',
  require('../../lib/addressService/addressService').default.name,
  require('../../../shared/popupErrorService/popupErrorService').default.name
];

export default angular.module('boss.lk.ProductionCtrl', dependencies)
  .controller('ProductionCtrl', function ProductionCtrl($scope, $filter, $state, toaster, userService, popupErrorService, addressService, userInfo, countries) {
    $scope.user = _.cloneDeep(userInfo);
    $scope.countries = countries;
    $scope.user.sameAddress = addressService.isTheSame($scope.user);

    $scope.type = $scope.user.customer_type !== 'private';

    $scope.$watch('type', function (newVal, oldVal) {
      if (newVal !== oldVal) {
        if (newVal) {
          $scope.user.customer_type = 'entity';
        } else {
          $scope.user.customer_type = 'private';
        }
      }
    });

    $scope.$watch('user.sameAddress', function (newVal, oldVal) {
      if ($scope.type && newVal !== oldVal) {
        if (newVal) {
          addressService.set($scope.user, true);
        }
      }
    });

    $scope.toProduction = function (form) {
      if ($scope.user.sameAddress) {
        addressService.set($scope.user, true);
      }
      userService.update($scope.user)
        .then(function (updatedUserInfo) {
          form.$resetSubmittingState();
          angular.copy(updatedUserInfo, $scope.user);
          angular.copy(updatedUserInfo, userInfo);
          $scope.user.sameAddress = addressService.isTheSame($scope.user);
          userService.makeProd()
            .then(function (anotherUserInfo) {
              angular.copy(anotherUserInfo, $scope.user);
              angular.copy(anotherUserInfo, userInfo);
              toaster.pop({
                type: 'success',
                title: $filter('translate')('To enable operation mode, you need to make an advance payment'),
                timeout: 0
              });
              $state.go('production2');
            })
            .catch(function (err) {
              popupErrorService.show(err);
            });
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
