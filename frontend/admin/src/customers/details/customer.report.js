const dependencies = [
  'angular-loading-bar',
  'toaster',
  'boss.const',
  require('../../../lib/customerService/customerService').default.name,
  require('../../../../shared/appGlobalState/appGlobalState').default.name
];

export default angular.module('boss.admin.customer.report', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.report', {
        url: '/report?after?before',
        views: {
          'detail': {
            template: require('./customer.report.tpl.html'),
            controller: 'MainDetailsReportCtrl'
          }
        }
      });
  })
  .controller('MainDetailsReportCtrl', function ($scope, customer, customerService, $stateParams, cfpLoadingBar, toaster, appGlobalState, CONST) {
    $scope.report = false;
    $scope.customer = customer;
    $scope.reportFormat = appGlobalState.defaultReportFormat || 'tsv';
    $scope.typeDetailed = false;

    loadReportData();

    $scope.$watch('reportFormat', function (newValue) {
      appGlobalState.defaultReportFormat = newValue;
    });

    $scope.getReport = function () {
      var reportType = $scope.typeDetailed ? 'detailed' : 'simple';
      cfpLoadingBar.start();
      customerService.downloadReport(customer, $stateParams.after * 1000, $stateParams.before * 1000, $scope.reportFormat, reportType)
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          toaster.pop('error', e.localized_message);
          cfpLoadingBar.complete();
        });
    };

    function loadReportData() {
      if (!$stateParams.after) {
        $stateParams.after = Math.round((new Date() - CONST.constants.month * 1000) / 1000);
        $stateParams.before = Math.round(new Date() / 1000);
      }
      if (!$stateParams.before) {
        $stateParams.before = Math.round(new Date() / 1000);
      }
      customerService.getJSONReport(customer, $stateParams.after * 1000, $stateParams.before * 1000)
        .then(function (rsp) {
          $scope.report = rsp.report;
        });
    }
  });
