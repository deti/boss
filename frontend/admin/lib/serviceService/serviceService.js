const dependencies = [
  'restangular',
  require('../tariffService/tariffService').default.name
];

export default angular.module('boss.serviceService', dependencies)
  .factory('serviceService', function (Restangular, tariffService, $q) {
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'service' && operation === 'getList') {
        var extractedData = data.service_list.items;
        extractedData.total = data.service_list.total;
        extractedData.perPage = data.service_list.per_page;
        extractedData.page = data.service_list.page;
        return extractedData;
      }
      if (what === 'category' && operation === 'getList') {
        return data.category_list;
      }
      return data;
    });

    function getNextPage(page, items, params) {
      var nextPage = page + 1;
      return Restangular.all('service').getList(angular.extend(params, {page: nextPage}))
        .then(nextPageItems => {
          nextPageItems.forEach(value => {
            items.push(value);
          });
          if (items.total > items.length) {
            return getNextPage(nextPage, items, params);
          } else {
            return $q.when(items);
          }
        });
    }

    return {
      list: function (params = {}) {
        return Restangular.all('service').getList(params);
      },
      fullList: function (params = {}) {
        return Restangular.all('service').getList(params)
        .then(items => {
          var pages = Math.ceil(parseInt(items.total) / parseInt(items.perPage));
          if (pages > 1) {
            return getNextPage(items.page, items, params);
          } else {
            return items;
          }
        });
      },
      createCustom: function (name, description, measure) {
        return Restangular.one('service').one('custom').customPOST({
          localized_name: name,
          description,
          measure
        });
      },
      createFlavor: function (flavor) {
        return Restangular.one('service').one('vm').customPOST(flavor);
      },
      editCustom: function (service) {
        var params = {
          localized_name: service.localized_name,
          description: service.description
        };
        if (service.mutable) {
          params.measure = service.measure.measure_id;
        }
        return Restangular.one('service').one(service.service_id.toString()).one('custom').customPUT(params);
      },
      editFlavor: function (flavor) {
        return Restangular.one('service', flavor.service_id).one('vm').customPUT({
          localized_name: flavor.localized_name,
          description: flavor.description
        });
      },
      tariffsWithService: function (service) {
        return tariffService.getList()
          .then(function (tariffs) {
            return tariffs.filter(tariff => {
              return _.find(tariff.services, item => item.service.service_id === service.service_id);
            });
          });
      },
      remove: function (service) {
        return Restangular.one('service', service.service_id).customDELETE();
      },
      categoriesList: function () {
        return Restangular.all('category').getList();
      },
      measures: function (params = {}) {
        return Restangular.one('measure').get(params)
          .then(function (rsp) {
            return rsp.measure_list;
          });
      },
      makeImmutable: function (id) {
        return Restangular.one('service', id).one('immutable').customPUT({
          service: id
        });
      }
    };
  });
