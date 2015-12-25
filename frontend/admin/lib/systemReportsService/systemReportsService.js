const dependencies = ['restangular'];

export default angular.module('boss.systemReportsService', dependencies)
  .factory('systemReportsService', function (Restangular) {
    return {
      getCustomerReport: function () {
        return Restangular.one('stat').one('customer').post()
        .then(function (rsp) {
          return rsp.customer_stats;
        });
      }
    };
  });
