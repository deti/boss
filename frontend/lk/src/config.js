const dependencies = [
  'restangular',
  'pascalprecht.translate',
  require('./const/const').default.name
];
const zeroClipboardPath = require('zeroclipboard/dist/ZeroClipboard.swf');
import {CONST} from './const/const';

export default angular.module('boss.lk.config', dependencies)
  .value('SERVER_USE_EXTERNAL_NETWORK', !CONST.floating_ips)
  .value('SHOW_DISK_SIZE_IN_FLAVOR', !CONST.manual_disk_size)
  .config(function (tmhDynamicLocaleProvider, $provide, ngClipProvider, $translateProvider, CONST, RestangularProvider, $locationProvider, $datepickerProvider, $httpProvider) {
    ngClipProvider.setPath(zeroClipboardPath);

    if (typeof ga !== 'undefined' && CONST.local.google_analytics && CONST.local.google_analytics.lk) {
      ga('create', CONST.local.google_analytics.lk, 'auto');
    }

    $provide.decorator('$state', function ($delegate, $rootScope) {
      $rootScope.$on('$stateChangeStart', function (event, state, params) {
        $delegate.next = state;
        $delegate.toParams = params;
      });
      return $delegate;
    });

    angular.extend($datepickerProvider.defaults, {
      dateFormat: 'dd.MM.yyyy'
    });

    RestangularProvider.setRequestSuffix('/');

    // IE caching GET requests fix
    if (!$httpProvider.defaults.headers.get) {
      $httpProvider.defaults.headers.get = {};
    }
    $httpProvider.defaults.headers.get['If-Modified-Since'] = 'Mon, 26 Jul 1997 05:00:00 GMT';
    $httpProvider.defaults.headers.get['Cache-Control'] = 'no-cache';
    $httpProvider.defaults.headers.get.Pragma = 'no-cache';

    $locationProvider.html5Mode({
      enabled: true,
      requireBase: false
    });

    if ((angular.mock || window.location.hostname === 'localhost') && window.Raven) {
      angular.extend(window.Raven, {
        config: function () {
          return this;
        },
        install: function () {
          return this;
        }
      });
    }

    tmhDynamicLocaleProvider.localeLocationPattern('/lk/angular-locale_{{locale}}.js');

    $translateProvider
      .translations('en-US', JSON.parse(require('../assets/translations/en.i18n.json')))
      .translations('ru-RU', JSON.parse(require('../assets/translations/ru.i18n.json')))
      .preferredLanguage(CONST.defaultLocale)
      .useLocalStorage()
      .useSanitizeValueStrategy(null);
  });
