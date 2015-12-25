const dependencies = ['restangular'];

export default angular.module('boss.currencyService', dependencies)
  .factory('currencyService', function (Restangular) {
    Restangular.addResponseInterceptor(function (data, operation, what, url) {
      if ((what === 'currency' || what === 'currency/active') && operation === 'getList') {
        return data.currencies;
      }
      return data;
    });

    return {
      list: function () {
        return Restangular.all('currency').getList();
      },
      activeCurrency: function () {
        return Restangular.one('currency/active').getList();
      }
    };
  });
