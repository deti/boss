const dependencies = [
  'restangular',
  require('../../../shared/appLocale/appLocale').default.name
];

export default angular.module('boss.utilityService', dependencies)
  .factory('utilityService', function (Restangular, appLocale) {
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'country' && operation === 'getList') {
        var localizedName = 'localized_name.' + appLocale.getLang(true);
        return _.sortBy(data.countries, localizedName);
      }
      return data;
    });
    return {
      countries: function () {
        return Restangular.all('country').withHttpConfig({cache: true}).getList();
      },
      roles: function () {
        return Restangular.one('role').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            return rsp.roles;
          });
      },
      customerLocales: function () {
        return Restangular.one('locale').one('active').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            var locales = [];
            _.forOwn(rsp.locale_list, (value, key) => {
              locales.push({code: key, localized_name: value});
            });
            return locales;
          });
      },
      quotasTemplates: function () {
        return Restangular.one('quotas').one('templates').get()
          .then(function (rsp) {
            return rsp.quotas_templates;
          });
      },
      customerMode: function () {
        return [
          {localized_name: {en: 'Test', ru: 'Тестовый'}, code: 'test'},
          {localized_name: {en: 'Product', ru: 'Продуктовый'}, code: 'product'}
        ];
      },
      withdrawPeriod: function (eventType) {
        return Restangular.one('event').one(eventType).one('allowed_period').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            return rsp.periods;
          });
      },
      testEmail: function (sendTo, sendCC, subject) {
        return Restangular.one('send_email').customPOST({
          send_to: sendTo,
          send_cc: sendCC,
          subject
        });
      },
      activeLanguages: function () {
        return Restangular.one('language').one('active').withHttpConfig({cache: true}).get()
          .then(function (rsp) {
            return rsp.language_list;
          });
      }
    };
  });
