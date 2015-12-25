const dependencies = [
  'restangular',
  require('../../../lib/customerService/customerService').default.name
];

export default angular.module('boss.admin.customer.bill', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.bill', {
        url: '/bill',
        views: {
          'detail': {
            template: require('./customer.bill.tpl.html'),
            controller: 'MainDetailsBillCtrl'
          }
        }
      });
  })
  .controller('MainDetailsBillCtrl', function ($scope, customer, customerService, Restangular) {
    $scope.accrued = null;
    $scope.customer = customer;
    $scope.amount = 0;
    $scope.comment = '';

    $scope.update = function (isAdd, form) {
      customerService.updateBalance(customer, $scope.amount * (isAdd ? 1 : -1), $scope.comment)
        .then(function (updatedCustomer) {
          Restangular.sync(updatedCustomer, customer);
          $scope.accrued = $scope.amount * (isAdd ? 1 : -1);
          $scope.comment = '';
          $scope.amount = 0;
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
