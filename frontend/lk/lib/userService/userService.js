const dependencies = [
  'restangular',
  'boss.const',
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../../shared/fileSaver/fileSaver').default.name,
  require('../../../shared/reportService/reportService').default.name
];

export default angular.module('boss.userService', dependencies)
  .factory('userService', function (Restangular, $q, $state, $filter, popupErrorService, reportService, CONST, fileSaver) {
    var Me = Restangular.all('customer').one('me');
    var userInfo = null;
    var lastUpdate = null;
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (operation === 'getList') {
        switch (what) {
          case 'country':
            data = data.countries;
            break;
          case 'subscription':
            data = data.subscriptions;
            break;
          case 'history':
            data = data.account_history;
        }
      }
      return data;
    });

    return {
      userInfo: function (update = false) {
        if (!update && userInfo) {
          return $q.when(userInfo);
        }
        return Me.get().then(function (rsp) {
          lastUpdate = Date.now();
          userInfo = rsp.customer_info;
          return userInfo;
        });
      },
      reload: function (userInfo) {
        if (Date.now() - lastUpdate < 1000) { // don't reload userInfo more often then 1 second
          return true;
        }
        return this.userInfo(true)
          .then(function (rsp) {
            if (!_.isEqual(rsp, userInfo)) {
              angular.copy(rsp, userInfo);
            }
          });
      },
      tariff: function () {
        return Me.one('tariff').get().then(function (rsp) {
          rsp.tariff_info.services.map(service => {
            var description = {};
            description.localized_name = service.service.description;
            service.service.description = description;
            return service;
          });
          return rsp.tariff_info;
        });
      },
      setLocale: function (locale) {
        return Me.customPUT({
          locale: locale
        });
      },
      subscriptions: function () {
        return Me.one('subscribe').get().then(function (rsp) {
          Object.keys(rsp.subscribe).forEach(key => {
            rsp.subscribe[key].email = rsp.subscribe[key].email.map(email => {
              return {text: email};
            });
          });
          return rsp.subscribe;
        });
      },
      updateSubscriptions: function (subscriptions) {
        Object.keys(subscriptions).forEach(key => {
          subscriptions[key].email = subscriptions[key].email.map(email => {
            return email.text;
          });
        });
        return Me.one('subscribe').customPUT({
          subscribe: subscriptions
        });
      },
      auth: function (login, password) {
        return Restangular.one('auth').post('', {
          email: login,
          password: password,
          return_customer_info: 'true'
        }).then(function (rsp) {
          userInfo = rsp.customer_info;
        });
      },
      update: function (user) {
        _.forEach(user.detailed_info, (val, key, obj) => {
          if (val === undefined) {
            obj[key] = null;
          }
        });
        return Me.customPUT({
          customer_type: user.customer_type,
          detailed_info: user.detailed_info
        }).then(function (rsp) {
          userInfo = rsp.customer_info;
          return rsp.customer_info;
        });
      },
      makeProd: function () {
        return Me.one('make_prod').post()
          .then(function (rsp) {
            userInfo = rsp.customer_info;
            return rsp.customer_info;
          });
      },
      updatePassword: function (oldPass, newPass) {
        return Me.customPUT({
          password: newPass
        });
      },
      logout: function () {
        return Restangular.one('logout').post().then(function () {
          userInfo = null;
        });
      },
      signup: function (user, recaptchaResponse) {
        return Restangular.one('customer').post('', {
          email: user.email,
          password: user.password,
          detailed_info: {
            telephone: (user.detailed_info ? user.detailed_info.telephone : null) || null
          },
          g_recaptcha_response: recaptchaResponse,
          promo_code: user.promo_code || null
        }).then(function (rsp) {
          userInfo = rsp.customer_info;
          return userInfo;
        });
      },
      confirmEmail: function (token) {
        return Restangular.one('customer').one('confirm_email').one(token).post('', {
          confirm_token: token
        });
      },
      sendConfirmEmail: function (token) {
        return Me.one('confirm_email').customPUT({
          confirm_token: token
        });
      },
      balanceHistory: function (params) {
        return Me.one('balance').all('history').getList(params);
      },
      resetPassword: function (email) {
        return Restangular.one('customer').customDELETE('password_reset', {
          email: email
        });
      },
      resetPasswordIsValid: function (key) {
        return Restangular.one('customer').one('password_reset').one(key).get()
          .then(function () {
            return true;
          })
          .catch(function () {
            return false;
          });
      },
      setPassword: function (key, password) {
        return Restangular.one('customer').one('password_reset').post(key, {
          password: password
        });
      },
      OSLogin: function () {
        return Me.one('os_login').get()
          .catch(function (err) {
            popupErrorService.show(err);
            return $q.reject(err);
          });
      },
      usedQuotas: function (force = false) {
        return Me.one('used_quotas').get({force})
          .then(function (rsp) {
            if (rsp.loading) {
              return {
                loading: true
              };
            }
            return rsp.used_quotas.map(group => {
              var key = Object.keys(group);
              group.name = key[0];
              return group;
            });
          })
          .catch(e => {
            return {
              error: true
            };
          });
      },
      downloadReport: function (startDate, endDate, format, reportType = 'simple') {
        return reportService.downloadReport(`${CONST.api}customer/me/report`, startDate, endDate, format, reportType);
      },
      getJSONReport: function (startDate, endDate, reportType = 'simple') {
        return reportService.getJSON(`${CONST.api}customer/me/report`, startDate, endDate, reportType)
        .then(rsp => {
          var report = rsp.report;
          var data = [], total = [];
          report.tariffs.forEach(item => {
            item.usage.forEach(usage => {
              usage.currency = item.currency;
              data.push(usage);
            });
          });

          if (report.total) {
            _.forOwn(report.total, function (value, key) {
              total.push({currency: key, sum: value});
            });
          }

          return {
            data, total
          };
        });
      },
      getAutoWithdraw: function () {
        return Me.one('payments').one('auto_withdraw').get();
      },
      setAutoWithdraw: function (data) {
        return Me.one('payments').one('auto_withdraw').customPOST(data);
      },
      restoreOSPassword: function () {
        return Me.one('reset_os_password').put();
      },
      downloadInvoice: function (amount, date = null, currency = null) {
        var dataToSend = {
          amount: amount.toString()
        };
        if (currency) {
          dataToSend.currency = currency;
        }
        if (date) {
          dataToSend.date = $filter('date')(date, 'yyyy-MM-ddTHH:mm:00');
        }
        return Me.one('invoice').customPOST(dataToSend)
          .then(function () {
            fileSaver.saveFileFromHttp({
              method: 'POST',
              url: `${CONST.api}customer/me/invoice/`,
              data: dataToSend
            });
          });
      },
      osToken() {
        return Restangular.one('customer').one('me').one('os_token').get()
          .then(response => {
            let token = response.token.id;
            let tenantId = response.token.tenant.id;
            return {token, tenantId};
          });
      }
    };
  });
