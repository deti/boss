const dependencies = [
  require('../serviceService/serviceService').default.name
];

export default angular.module('boss.categoriesWithServicesService', dependencies)
  .factory('categoriesWithServicesService', function (serviceService, $q) {
    function getServicesForCategory(category, services) {
      return _.filter(services, service => service.category.category_id === category.category_id)
        .map(service => {
          return _.extend({}, service, {
            price: 0,
            selected: false,
            need_changing: null
          });
        });
    }

    function mergeTariffServices(tariffServices, categories) {
      // warn if we have tariff services that are absent in categories list
      var services = [];
      categories.forEach(cat => {
        services = services.concat(cat.services);
      });
      tariffServices.forEach(tariffService => {
        var res = true;
        res = _.some(services, s => {
          return s.service_id === tariffService.service.service_id;
        });
        if (!res) {
          console.log('tariff service is not in the list of services', tariffService.service.localized_name.en);
          Raven.captureMessage('tariff service is not in the list of services', {extra: {tariff: tariffService.service.localized_name.en}});
        }
      });

      return categories.map(category => {
        var clone = _.clone(category);
        clone.services = category.services.map(service => {
          var serviceWrapper = _.find(tariffServices, tariffService => tariffService.service.service_id === service.service_id);
          if (!serviceWrapper) {
            return service;
          }
          return _.extend(service, {
            price: serviceWrapper.price,
            selected: true,
            need_changing: serviceWrapper.need_changing
          });
        });
        return clone;
      });
    }

    var getServicesByCategories = function () {
      return $q.all({
        categories: serviceService.categoriesList(),
        services: serviceService.fullList()
      }).then(function (result) {
        var categories = result.categories.plain();
        var services = result.services.plain();
        categories.forEach(category => {
          category.services = getServicesForCategory(category, services);
          return category;
        });
        return categories;
      });
    };

    return {
      get: getServicesByCategories,
      mergeTariffServices: mergeTariffServices
    };
  });
