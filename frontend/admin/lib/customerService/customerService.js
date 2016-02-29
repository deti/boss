const dependencies = [
  'restangular',
  require('../../../shared/reportService/reportService').default.name,
  require('../../../shared/fileSaver/fileSaver').default.name,
  require('../../src/const/const').default.name
];

export default angular.module('boss.customerService', dependencies)
  .factory('customerService', function (Restangular, $filter, $http, CONST, reportService, fileSaver) {
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'customer' && operation === 'getList') {
        var extractedData;
        extractedData = data.customer_list.items;
        extractedData.forEach(item => { // convert account balance to numbers
          if (!item.account) {
            return;
          }
          Object.keys(item.account).forEach(account => {
            Object.keys(item.account[account]).forEach(key => {
              item.account[account][key] = parseFloat(item.account[account][key]);
            });
          });
        });
        extractedData.total = data.customer_list.total;
        extractedData.perPage = data.customer_list.per_page;
        return extractedData;
      }
      return data;
    });
    Restangular.addRequestInterceptor(function (element, operation, what) {
      if (what === 'customer' && operation === 'put') {
        delete element.tariffInfo;
      }
      return element;
    });

    return {
      getCustomers: function (params = {}) {
        return Restangular.all('customer').getList(params);
      },
      getBalanceHistory: function (id, params = {}) {
        return Restangular.one('customer', id).one('balance').one('history').get(params).then(function (rsp) {
          return rsp.account_history;
        });
      },
      getHistory: function (id, params = {}) {
        return Restangular.one('customer', id).one('history').get(params).then(function (rsp) {
          return rsp.history;
        });
      },
      update: function (customer) {
        return customer.save();
      },
      getTariff: function (customerId) {
        return Restangular.one('customer', customerId).one('tariff').get().then(function (rsp) {
          return rsp.tariff_info;
        });
      },
      setDeferredTariff: function (customer, tariff, date) {
        date = $filter('date')(date, 'yyyy-MM-ddTHH:mm:00');
        return Restangular.one('customer', customer.customer_id).one('deferred').customPUT({
          // customer_id: customer.customer_id,
          tariff: tariff,
          date: date
        });
      },
      updateBalance: function (customer, amount, comment) {
        return Restangular.one('customer', customer.customer_id).one('balance').customPUT({
          amount: amount.toFixed(2),
          comment: comment
        }).then(function (rsp) {
          return rsp.customer_info;
        });
      },
      setBlocked: function (customer, isBlocked, message = '') {
        return Restangular.one('customer', customer.customer_id).one('block').customPUT({
          blocked: isBlocked,
          message
        });
      },
      archive: function (customer) {
        return customer.remove();
      },
      quotas: function (customer) {
        return Restangular.one('customer', customer.customer_id).one('quota').get()
          .then(function (rsp) {
            return rsp.quota;
          });
      },
      updateQuotas: function (customer, quotas) {
        var limits = {};
        quotas.forEach(quota => {
          limits[quota.limit_id] = quota.value;
        });
        return Restangular.one('customer', customer.customer_id).one('quota').customPUT({limits});
      },
      applyQuotaTemplate: function (customer, template) {
        return Restangular.one('customer', customer.customer_id).one('quota').customPOST({
          template
        });
      },
      resetPassword: function (customer) {
        return Restangular.setOneBaseUrl('/lk_api/0').one('customer').customDELETE('password_reset', {
          email: customer.email
        });
      },
      makeProd: function (customer) {
        return Restangular.one('customer', customer.customer_id).one('make_prod').customPOST()
          .then(function (rsp) {
            return rsp.customer_info;
          });
      },
      getSubscriptions: function (id) {
        return Restangular.one('customer', id).one('subscribe').get({customer: id})
          .then(function (rsp) {
            Object.keys(rsp.subscribe).forEach(key => {
              rsp.subscribe[key].email = rsp.subscribe[key].email.map(email => {
                return {text: email};
              });
            });
            return rsp.subscribe;
          });
      },
      updateSubscriptions: function (id, subscriptions) {
        Object.keys(subscriptions).forEach(key => {
          subscriptions[key].email = subscriptions[key].email.map(email => {
            return email.text;
          });
        });
        return Restangular.one('customer', id).one('subscribe').customPUT({
          customer: id,
          subscribe: subscriptions
        });
      },
      downloadReport: function (customer, startDate, endDate, format, reportType = 'simple') {
        return reportService.downloadReport(`${CONST.api}customer/${customer.customer_id}/report`, startDate, endDate, format, reportType);
      },
      getJSONReport: function (customer, startDate, endDate, reportType = 'simple') {
        return reportService.getJSON(`${CONST.api}customer/${customer.customer_id}/report`, startDate, endDate, reportType);
      },
      createCustomer: function (customer) {
        return Restangular.one('customer').post('', {
          email: customer.contacts.email,
          detailed_info: customer.detailed_info,
          make_prod: customer.customer_mode === 'product',
          customer_type: customer.customer_type,
          withdraw_period: customer.withdraw_period,
          locale: customer.locale
        });
      },
      recreateCloud: function (customer) {
        return Restangular.one('customer', customer.customer_id).one('recreate_tenant').post('', {
          customer: customer.customer_id
        });
      },
      sendConfirmEmail: function (customerId) {
        return Restangular.one('customer', customerId).one('confirm_email').put();
      },
      downloadInvoice: function (customerId, amount, currency, date = null) {
        if (date) {
          date = $filter('date')(date, 'yyyy-MM-ddTHH:mm:00');
        }
        var dataToSend = {
          amount: amount.toString()
        };
        if (currency) {
          dataToSend.currency = currency;
        }
        if (date) {
          dataToSend.date = date;
        }
        return Restangular.one('customer', customerId).one('invoice').customPOST(dataToSend)
          .then(function () {
            fileSaver.saveFileFromHttp({
              method: 'POST',
              url: `${CONST.api}customer/${customerId}/invoice/`,
              data: dataToSend
            });
          });
      },
      getDeferredChanges: function (customerId) {
        return Restangular.one('customer', customerId).one('deferred').get()
          .then(function (rsp) {
            return rsp.deferred;
          });
      },
      setGroupTariff: function (customers, tariffId) {
        return Restangular.one('customer').one('group').customPUT({
          customers: customers,
          tariff: tariffId
        });
      }
    };
  });
