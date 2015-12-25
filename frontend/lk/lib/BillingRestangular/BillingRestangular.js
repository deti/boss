const dependencies = ['restangular'];

export default angular.module('BillingRestangular', dependencies)
  .factory('BillingRestangular', function (Restangular) {
    return Restangular.withConfig(function (RestangularConfigurer) {
      RestangularConfigurer.setBaseUrl('/api/0/');
    });
  });
