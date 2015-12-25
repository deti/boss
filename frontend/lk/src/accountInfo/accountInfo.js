import 'angular-duration-format/dist/angular-duration-format'
const dependencies = [
  'angular-duration-format.filter',
  require('../../lib/bsPopupDetails/bsPopupDetails').default.name
];

export default angular.module('boss.accountInfo', dependencies)
  .controller('AccountInfoCtrl', function AccountInfoCtrl($scope, userService, utilityService, $filter, CONST, $interval) {
    $scope.accountInfo = {
      title: $filter('translate')('Account balance'),
      description: $filter('translate')('The balance at the top section is the difference between the funds available in your account and the cost of provided services'),
      details: []
    };

    function setAccountDetails() {
      var updatedDetails;
      if ($scope.user.account[$scope.user.currency]) {
        updatedDetails = [
          {
            name: $filter('translate')('Funds to be withdrawn from your account'),
            templateValue: $scope.period,
            filter: 'localizedName'
          },
          {
            name: $filter('translate')('Funds available'),
            templateValue: $scope.user.account[$scope.user.currency].balance,
            filter: {name: 'money', args: [$scope.user.currency]},
            note: $filter('translate')('(by the time of the last withdrawal)')
          },
          {
            name: $filter('translate')('Spending'),
            templateValue: $scope.user.account[$scope.user.currency].withdraw,
            filter: {name: 'money', args: [$scope.user.currency]},
            note: $filter('translate')('(at the moment, updated every hour)')
          },
          {
            name: $filter('translate')('Account balance'),
            templateValue: $scope.user.account[$scope.user.currency].current,
            filter: {name: 'money', args: [$scope.user.currency]},
            note: $filter('translate')('(at the moment, updated every hour)')
          },
          {
            name: $filter('translate')('The date of the next withdrawal'),
            templateValue: $scope.user.withdraw_date,
            filter: {name: 'date', args: ['short']}
          }
        ];
        $scope.accountInfo.details = updatedDetails;
      }
    }

    if (!$scope.user.blocked && $scope.user.customer_mode == 'test') {
      $scope.testTime = CONST.local.test_period * 1000 - (new Date() - new Date($scope.user.created));
      $interval(function () {
        $scope.testTime = CONST.local.test_period * 1000 - (new Date() - new Date($scope.user.created));
      }, 1000 * 15);
    }

    $scope.$watch('user.account[user.currency]', function (newValue, oldValue) {
      if (newValue) {
        setAccountDetails();
      }
    });
    $scope.$watch('user.tariff_id', function (newValue, oldValue) {
      if (newValue !== oldValue) {
        userService.tariff()
          .then(function (rsp) {
            angular.copy(rsp, $scope.tariff);
          });
      }
    });
    $scope.$watch('user.withdraw_period', function (newValue, oldValue) {
      if (newValue !== oldValue) {
        utilityService.getLocalizedPeriod(newValue)
          .then(function (rsp) {
            angular.copy(rsp, $scope.period);
            setAccountDetails();
          });
      }
    });
  });
