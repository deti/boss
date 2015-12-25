const dependencies = ['restangular'];

export default angular.module('boss.tariffService', dependencies)
  .constant('TARIFF_STATE', {
    'NEW': {localized_name: {en: 'New', ru: 'Новый'}, value: 'new'},
    'ACTIVE': {localized_name: {en: 'Active', ru: 'Действующий'}, value: 'active'},
    'ARCHIVED': {localized_name: {en: 'In archive', ru: 'В архиве'}, value: 'archived'}
  })
  .factory('tariffService', function (Restangular, TARIFF_STATE, $q) {
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'tariff' && operation === 'getList') {
        var extractedData = data.tariff_list.items;
        extractedData.total = data.tariff_list.total;
        extractedData.perPage = data.tariff_list.per_page;
        extractedData.page = data.tariff_list.page;
        return extractedData;
      }
      return data;
    });

    function getServices(categories, mutableOnly = false) {
      return _.flatten(categories.map(category => {
        return _.filter(category.services, service => mutableOnly ? service.selected && service.need_changing : service.selected)
          .map(service => {
            return {service_id: service.service_id, price: service.price};
          });
      }));
    }

    function getNextPage(page, items, params) {
      var nextPage = page + 1;
      return Restangular.all('tariff').getList(angular.extend(params, {page: nextPage}))
        .then(nextPageItems => {
          nextPageItems.forEach(value => {
            items.push(value);
          });
          if (items.total > items.length) {
            return getNextPage(nextPage, items, params);
          } else {
            items.map(getTariffStatus);
            return $q.when(items);
          }
        });
    }

    function getTariffStatus(item) {
      item.users = (item.used !== undefined) ? item.used : null;
      if (item.deleted === null) {
        if (item.mutable) {
          item.status = TARIFF_STATE.NEW;
        } else {
          item.status = TARIFF_STATE.ACTIVE;
        }
      } else {
        item.status = TARIFF_STATE.ARCHIVED;
      }
      return item;
    }

    return {
      getList: function (params = {}) {
        return Restangular.all('tariff').getList(angular.extend({show_used: true}, params))
        .then(items => {
          items.map(getTariffStatus);
          return items;
        });
      },
      getFullList: function (params = {}) {
        return Restangular.all('tariff').getList(params)
        .then(items => {
          var pages = Math.ceil(parseInt(items.total) / parseInt(items.perPage));
          if (pages > 1) {
            return getNextPage(items.page, items, params);
          } else {
            items.map(getTariffStatus);
            return items;
          }
        });
      },
      createTariff: function (tariff, categories) {
        var services = categories ? getServices(categories, false) : null;
        return Restangular.all('tariff').post({
          localized_name: tariff.localized_name,
          description: tariff.description,
          currency: tariff.currency,
          parent_id: tariff.currentParent || null,
          services: services
        });
      },
      updateTariff: function (tariff, categories) {
        var services = categories ? getServices(categories, false) : null;
        return Restangular.one('tariff').customPUT({
          tariff: tariff.tariff_id,
          description: tariff.description || null,
          localized_name: tariff.localized_name || null,
          currency: tariff.currency || null,
          services: services
        }, tariff.tariff_id);
      },
      updateMutableServices: function (tariffId, categories, oldCategories, formController) {
        var services = categories ? getServices(categories, true) : null;
        var oldServices = oldCategories ? getServices(oldCategories, true) : null;

        var updatedServices = _.filter(services, service => {
          var oldPrice = _.find(oldServices, oldService => oldService.service_id === service.service_id).price;
          return (service.price !== oldPrice || formController[service.service_id].$dirty);
        });
        return Restangular.one('tariff').customPUT({
          services: updatedServices
        }, tariffId);
      },
      archiveTariff: function (id) {
        return Restangular.one('tariff', id).remove({tariff: id});
      },
      defaultTariff: function (id) {
        return Restangular.one('tariff', id).one('default').put({tariff: id});
      },
      activateTariff: function (id) {
        return Restangular.one('tariff', id).one('immutable').put({tariff: id});
      },
      history: function (id, params) {
        return Restangular.one('tariff', id).one('history').get(params)
          .then(function (rsp) {
            return rsp.tariff_history;
          });
      }
    };
  });
