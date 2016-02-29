const dependencies = [
  'tmh.dynamicLocale',
  'pascalprecht.translate',
  'ipCookie'
];

export default angular.module('boss.appLocale', dependencies)
  .value('DEFAULT_LOCALE', 'en-US')
  .factory('appLocale', function ($translate, tmhDynamicLocale, $q, $log, $window, ipCookie, DEFAULT_LOCALE) {
    var localeLoaded = false;

    function loadLocale() {
      return $translate('E-mail')
        .then(function () {
          ipCookie('horizon_language', langFromLocale($translate.use().toLowerCase()), {path: '/'});
          return tmhDynamicLocale.set($translate.use().toLowerCase());
        })
        .then(function () {
          localeLoaded = $translate.use();
          return localeLoaded;
        });
    }

    function getLocale(immediately = false) {
      if (immediately) {
        if (!localeLoaded) {
          $log.warn('Trying to get locale before loaded');
        }
        return localeLoaded || defaultLocale();
      }
      if (localeLoaded) {
        return $q.when(localeLoaded);
      }
      return loadLocale();
    }

    function getLang(immediately = false) {
      if (immediately) {
        return langFromLocale(getLocale(true));
      }
      return getLocale()
        .then(function (locale) {
          return langFromLocale(locale);
        });
    }

    function getBackendLocale(immediately = false) {
      if (immediately) {
        return localeToBackend(getLocale(true));
      }
      return getLocale()
        .then(function (locale) {
          return localeToBackend(locale);
        });
    }

    function langFromLocale(locale) {
      return locale.split('-')[0];
    }

    function localeFromLang(lang) {
      var map = {
        en: 'en-US',
        ru: 'ru-RU'
      };
      lang = lang.toLowerCase();
      var locale = map[lang];
      if (locale === undefined) {
        console.warn(`Trying to convert lang ${lang} to locale, can not map it to any known locale.`);
        locale = map[defaultLang()];
      }
      return locale;
    }

    function localeToBackend(locale) {
      return locale.replace('-', '_').toLowerCase();
    }

    function setLocale(locale) {
      $translate.use(locale)
        .then(function () {
          ipCookie('horizon_language', langFromLocale(locale), {path: '/'});
          localeLoaded = locale;
          $window.location.reload();
        });
    }

    function setLang(lang) {
      setLocale(localeFromLang(lang));
    }

    function defaultLocale() {
      return DEFAULT_LOCALE;
    }

    function defaultLang() {
      langFromLocale(defaultLocale());
    }

    return {
      load: loadLocale,
      getLocale: getLocale,
      getLang: getLang,
      getBackendLocale: getBackendLocale,
      defaultLocale: defaultLocale,
      defaultLang: defaultLang,
      setLocale: setLocale,
      setLang: setLang,
      localeToBackend: localeToBackend
    };
  });
