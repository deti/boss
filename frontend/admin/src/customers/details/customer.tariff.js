const dependencies = [
  'toaster',
  require('../../../lib/tariffService/tariffService').default.name,
  require('../../../lib/customerService/customerService').default.name
];

export default angular.module('boss.admin.customer.tariff', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.tariff', {
        url: '/tariff',
        views: {
          'detail': {
            template: require('./customer.tariff.tpl.html'),
            controller: 'MainDetailsTariffCtrl'
          }
        },
        resolve: {
          tariffs: function (tariffService) {
            return tariffService.getFullList();
          },
          deferred: function (customerService, customer) {
            return customerService.getDeferredChanges(customer.customer_id);
          }
        }
      });
  })
  .controller('MainDetailsTariffCtrl', function ($scope, customer, tariffs, deferred, toaster, customerService, TARIFF_STATE, $filter) {
    $scope.deferred = deferred;
    $scope.tariffs = _.where(tariffs, {status: TARIFF_STATE.ACTIVE});
    $scope.tariff = customer.tariff_id;

    $scope.changeLater = false;
    $scope.currentDate = new Date();
    $scope.currentDate.setDate($scope.currentDate.getDate() - 1);
    $scope.changeDate = {
      date: new Date(),
      hour: 0,
      minute: 0
    };
    $scope.changeDate.hour = ($scope.changeDate.date.getHours() + 1).toString();
    $scope.hours = _.range(0, 24);
    $scope.minutes = _.range(0, 60, 5);

    $scope.updateTariff = function (form) {
      if (!form.$valid) {
        return;
      }
      var promise;
      if ($scope.changeLater === false) {
        customer.tariff = $scope.tariff;
        promise = customer.save();
      } else {
        var date = $scope.changeDate.date;
        date.setHours($scope.changeDate.hour - 3);
        date.setMinutes($scope.changeDate.minute);
        promise = customerService.setDeferredTariff(customer, $scope.tariff, date);
      }
      promise.then(function (rsp) {
        customer.tariff_id = $scope.tariff;
        customer.currency = _.result(_.findWhere($scope.tariffs, {tariff_id: $scope.tariff}), 'currency', customer.currency);
        if ($scope.changeLater) {
          $scope.deferred = rsp.deferred ? rsp.deferred : null;
        }
        toaster.pop('success', $scope.changeLater ? $filter('translate')('Plan change is scheduled') : $filter('translate')('Plan is successfully changed'));
      }).catch(function (rsp) {
        form.$parseErrors(rsp);
      });
    };
  });
