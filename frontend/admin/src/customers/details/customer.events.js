const dependencies = [
  'restangular',
  require('../../../lib/customerService/customerService').default.name
];

export default angular.module('boss.admin.customer.events', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.events', {
        url: '/events',
        views: {
          'detail': {
            template: require('./customer.events.tpl.html'),
            controller: 'MainDetailsEventsCtrl'
          }
        },
        resolve: {
          subscriptionsData: function (customerService, customer) {
            return customerService.getSubscriptions(customer.customer_id);
          }
        }
      });
  })
  .controller('MainDetailsEventsCtrl', function ($scope, subscriptionsData, customer, customerService, $q, toaster, Restangular, $filter) {
    $scope.customer = Restangular.copy(customer);
    $scope.subscriptions = subscriptionsData;

    $scope.updateSubscriptions = function (form) {
      var promises = [];
      promises.push(customerService.updateSubscriptions(customer.customer_id, $scope.subscriptions));
      if (form.balance_limit.$dirty) {
        promises.push(updateCreditLimit());
      }

      $q.all(promises)
        .then(function () {
          toaster.pop('success', $filter('translate')('Information was successfully updated'));
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    function updateCreditLimit() {
      return customerService.update($scope.customer)
        .then(function () {
          Restangular.sync($scope.customer, customer);
        });
    }
  });
