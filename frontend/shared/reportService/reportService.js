import moment from 'moment';
const dependencies = [
  require('../fileSaver/fileSaver').default.name
];

export default angular.module('boss.reportService', dependencies)
  .value('REPORT_API_URL', '/api/')
  .factory('reportService', function ($http, fileSaver, $q, $timeout, REPORT_API_URL) {
    function getReport(httpConfig, count = 0) {
      var defer = $q.defer();
      if (count > 40) { // 1 minute
        defer.reject('error');
        return defer.promise;
      }
      $http(httpConfig).success(data => {
        if (data.status && data.status !== 'completed') {
          if (data.status === 'error') {
            defer.reject('error');
            return;
          }
          $timeout(() => {
            getReport(httpConfig, count + 1)
              .then(function (rsp) {
                defer.resolve(rsp);
              })
              .catch(function (e) {
                defer.reject(e);
              });
          }, 1500);
          return;
        }
        defer.resolve(data);
      }).error(function (e) {
        defer.reject(e);
      });
      return defer.promise;
    }

    function formatDate(date) {
      const m = moment(date);
      return m.utc().format('YYYY-MM-DDTHH');
    }

    return {
      downloadReport: function downloadReport(url, startDate, endDate, format, reportType = 'simple') {
        var httpConfig = {
          method: 'POST',
          url: url,
          ignoreLoadingBar: true,
          data: {
            start: formatDate(startDate),
            finish: formatDate(endDate),
            report_format: format,
            report_type: reportType
          }
        };
        return getReport(httpConfig)
          .then(function () {
            fileSaver.saveFileFromHttp(httpConfig);
            return true;
          });
      },
      getJSON: function (url, startDate, endDate, reportType = 'simple') {
        var httpConfig = {
          method: 'POST',
          url: url,
          ignoreLoadingBar: true,
          data: {
            start: formatDate(startDate),
            finish: formatDate(endDate),
            report_format: 'json',
            report_type: reportType
          }
        };
        return getReport(httpConfig);
      },
      getJSONOpenstackUsage: function (locale) {
        var httpConfig = {
          method: 'POST',
          url: `${REPORT_API_URL}stat/openstack/usage`,
          ignoreLoadingBar: true,
          data: {
            locale,
            report_format: 'json'
          }
        };
        return getReport(httpConfig)
          .then(rsp => {
            var data = [];
            _.forOwn(rsp.report.tenant_usage, (value, key) => {
              if (!value.tenant) {
                value.tenant = {};
              }
              value.tenant.id = key;
              data.push(value);
            });
            return data;
          });
      },
      downloadReceipts: function (startDate, endDate, locale, format = 'tsv') {
        var httpConfig = {
          method: 'POST',
          url: `${REPORT_API_URL}report/receipts`,
          ignoreLoadingBar: true,
          data: {
            start: formatDate(startDate),
            finish: formatDate(endDate),
            report_format: format,
            locale
          }
        };
        return getReport(httpConfig)
          .then(function () {
            fileSaver.saveFileFromHttp(httpConfig);
            return true;
          });
      },
      downloadUsage: function (startDate, endDate, locale, format = 'tsv') {
        var httpConfig = {
          method: 'POST',
          url: `${REPORT_API_URL}report/usage`,
          ignoreLoadingBar: true,
          data: {
            start: formatDate(startDate),
            finish: formatDate(endDate),
            report_format: format,
            locale
          }
        };
        return getReport(httpConfig)
          .then(function () {
            fileSaver.saveFileFromHttp(httpConfig);
            return true;
          });
      }
    };
  });
