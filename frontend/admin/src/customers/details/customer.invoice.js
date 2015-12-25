const dependencies = [
  'angular-loading-bar',
  'toaster',
  require('../../../lib/customerService/customerService').default.name
];

export default angular.module('boss.admin.customer.invoice', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.invoice', {
        url: '/invoice',
        views: {
          'detail': {
            template: require('./customer.invoice.tpl.html'),
            controller: 'MainDetailsInvoiceCtrl'
          }
        },
        resolve: {
          activeCurrency: function (currencyService) {
            return currencyService.activeCurrency();
          }
        }
      });
  })
  .controller('MainDetailsInvoiceCtrl', function MainDetailsInvoiceCtrl($scope, activeCurrency, customer, customerService, toaster, cfpLoadingBar) {
    $scope.activeCurrency = activeCurrency;
    $scope.customer = customer;
    $scope.amount = 0;
    $scope.currency = customer.currency;
    $scope.date = new Date();

    $scope.downloadInvoice = function (form) {
      customerService.downloadInvoice(customer.customer_id, $scope.amount, $scope.currency, $scope.date)
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.downloadAcceptance = function () {
      cfpLoadingBar.start();
      customerService.downloadReport(customer, $scope.startDate, $scope.endDate, 'pdf', 'acceptance_act')
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          toaster.pop('error', e.localized_message);
          cfpLoadingBar.complete();
        });
    };
  });
