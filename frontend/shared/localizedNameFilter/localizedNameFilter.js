const dependencies = [
  require('../appLocale/appLocale').default.name
];

export default angular.module('boss.localizedNameFilter', dependencies)
  .filter('localizedName', function (appLocale) {
    return function (input, fieldName = 'localized_name') {
      var defaultLang = appLocale.defaultLang();
      if (typeof input[fieldName] === 'undefined') {
        throw new Error(`Value should contain '${fieldName}' field`);
      }
      var lang = appLocale.getLang(true),
        localizedName = input[fieldName];
      if (typeof localizedName[lang] !== 'undefined') {
        return localizedName[lang];
      } else if (typeof localizedName[defaultLang] !== 'undefined') {
        return localizedName[defaultLang];
      } else {
        return '';
      }
    };
  });
