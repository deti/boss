const dependencies = [
  'restangular',
  'pascalprecht.translate',
  require('./const/const').default.name
];
import {CONST} from './const/const';
const tagsInputTplPath = require('./views/tags-input.partial.tpl.html');
const zeroClipboardPath = require('zeroclipboard/dist/ZeroClipboard.swf');

export default angular.module('boss.admin.config', dependencies)
  .value('REPORT_API_URL', CONST.api)
  .config(function (RestangularProvider, $locationProvider, $translateProvider, CONST, $datepickerProvider, cfpLoadingBarProvider, $httpProvider, tmhDynamicLocaleProvider, $provide, ngClipProvider) {
    ngClipProvider.setPath(zeroClipboardPath);
    if (typeof ga !== 'undefined') {
      ga('create', CONST.local.google_analytics.admin, 'auto');
    }

    $provide.decorator('$state', function ($delegate, $rootScope) {
      $rootScope.$on('$stateChangeStart', function (event, state, params) {
        $delegate.next = state;
        $delegate.toParams = params;
      });
      return $delegate;
    });

    $provide.decorator('tagsInputDirective', function ($delegate) {
      $delegate[0].templateUrl = tagsInputTplPath;
      return $delegate;
    });


    angular.extend($datepickerProvider.defaults, {
      dateFormat: 'dd.MM.yyyy'
    });

    cfpLoadingBarProvider.includeSpinner = false;

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

    tmhDynamicLocaleProvider.localeLocationPattern('/admin/angular-locale_{{locale}}.js');

    $translateProvider
      .translations('en-US', JSON.parse(require('../assets/translations/en.i18n.json')))
      .translations('ru-RU', JSON.parse(require('../assets/translations/ru.i18n.json')))
      .preferredLanguage(CONST.defaultLocale)
      .useLocalStorage()
      .useSanitizeValueStrategy(null);
  });
