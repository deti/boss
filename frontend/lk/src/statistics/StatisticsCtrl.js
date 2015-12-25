const dependencies = [
  'ui.router',
  'angular-loading-bar',
  'toaster',
  'boss.const',
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../../shared/appLocale/appLocale').default.name,
  require('../../lib/userService/userService').default.name
];

export default angular.module('boss.lk.StatisticsCtrl', dependencies)
  .controller('StatisticsCtrl', function StatisticsCtrl($scope, $filter, $stateParams, cfpLoadingBar, toaster, $q,
                                                        userService, appLocale, CONST, popupErrorService) {
    $scope.reportFormat = 'tsv';
    $scope.typeDetailed = false;
    $scope.data = false;
    $scope.displayedData = [];

    $scope.downloadReport = function () {
      var reportType = $scope.typeDetailed ? 'detailed' : 'simple';
      cfpLoadingBar.start();
      userService.downloadReport($stateParams.after * 1000, $stateParams.before * 1000, $scope.reportFormat, reportType)
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          toaster.pop('error', e.localized_message);
          cfpLoadingBar.complete();
        });
    };

    loadReport()
      .then(rsp => {
        $scope.total = rsp.total;
        $scope.data = rsp.data;
      });

    $scope.columns = [
      {field: 'name', title: $filter('translate')('Service')},
      {field: 'total_usage_volume', title: $filter('translate')('Used'), filter: 'number', width: 200},
      {field: 'measure', title: $filter('translate')('Measurement unit'), width: 200},
      {
        field: 'price', title: $filter('translate')('Price per unit'),
        value: function (item) {
          return $filter('money')(item.price, item.currency);
        },
        width: 200
      },
      {
        field: 'total_cost',
        title: $filter('translate')('Total cost'),
        value: function (item) {
          return $filter('money')(item.total_cost, item.currency);
        },
        width: 200
      }
    ];

    function loadReport() {
      if (!$stateParams.after) {
        $stateParams.after = Math.round((new Date() - CONST.constants.week * 1000) / 1000);
        $stateParams.before = Math.round(new Date() / 1000);
      }
      if (!$stateParams.before) {
        $stateParams.before = Math.round(new Date() / 1000);
      }
      return userService.setLocale(appLocale.getBackendLocale(true))
        .then(function () {
          cfpLoadingBar.start();
          cfpLoadingBar.set(0.01);
          return userService.getJSONReport($stateParams.after * 1000, $stateParams.before * 1000);
        })
        .then(function (rsp) {
          cfpLoadingBar.complete();
          return rsp;
        })
        .catch(function (err) {
          cfpLoadingBar.complete();
          popupErrorService.show(err);
          return $q.reject(err);
        });
    }
  });
