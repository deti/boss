const dependencies = [
  require('../BillingRestangular/BillingRestangular').default.name,
  require('../../../shared/appLocale/appLocale').default.name
];

export default angular.module('boss.utilityService', dependencies)
  .factory('utilityService', function (BillingRestangular, Restangular, appLocale) {
    BillingRestangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'country' && operation === 'getList') {
        var localizedName = 'localized_name.' + appLocale.getLang(true);
        return _.sortBy(data.countries, localizedName);
      }
      return data;
    });
    return {
      countries: function () {
        return BillingRestangular.all('country').withHttpConfig({cache: true}).getList();
      },
      subscriptionsInfo: function () {
        return BillingRestangular.one('subscription').get()
          .then(function (rsp) {
            return rsp.subscriptions;
          });
      },
      getLocalizedPeriod: function (id) {
        return BillingRestangular.one('event').one('auto_report').one('allowed_period').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            var localizedPeriod = _.result(_.find(rsp.periods, 'period_id', id), 'localized_name');
            return {
              localized_name: localizedPeriod
            };
          });
      },
      activeLanguages: function () {
        return Restangular.one('language').one('active').get()
          .then(function (rsp) {
            return rsp.language_list;
          });
      },
      withdrawPeriod: function (eventType) {
        return BillingRestangular.one('event').one(eventType).one('allowed_period').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            return rsp.periods;
          });
      },
      locales: function () {
        return Restangular.one('locale').one('active').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            var locales = [], localizedName;
            _.forOwn(rsp.locale_list, (value, key) => {
              locales.push({code: key, localized_name: value});
            });
            localizedName = 'localized_name.' + appLocale.getLang(true);
            return _.sortBy(locales, localizedName);
          });
      }
    };
  });
