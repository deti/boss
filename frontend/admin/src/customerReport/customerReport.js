const dependencies = [
  require('../../lib/systemReportsService/systemReportsService').default.name
];

export default angular.module('boss.admin.customerReport', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('customerReport', {
        parent: 'boss',
        url: '/customer-report',
        views: {
          'main@boss': {
            controller: 'CustomerReportCtrl',
            template: require('./customerReport.tpl.html')
          }
        },
        data: {
          pageTitle: 'Customers report'
        },
        resolve: {
          customerReport: function (systemReportsService) {
            return systemReportsService.getCustomerReport();
          }
        }
      });
  })
  .controller('CustomerReportCtrl', function ($scope, customerReport) {
    $scope.customerReport = customerReport;
  });
