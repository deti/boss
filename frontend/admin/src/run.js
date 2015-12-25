const dependencies = [
  'restangular',
  'ui.router',
  'angular-loading-bar',
  require('./const/const').default.name,
  require('../../shared/appLocale/appLocale').default.name
];

export default angular.module('boss.admin.run', dependencies)
  .run(function (CONST, $rootScope, $state, $stateParams, $window, $timeout, $log, Restangular, cfpLoadingBar, appLocale, $location, $datepicker, appGlobalState) {
    appLocale.load()
      .then(function (locale) {
        if (locale === 'ru-RU') {
          angular.extend($datepicker.defaults, {
            startWeek: 1
          });
        }
      });
    $rootScope.CONST = CONST;
    $rootScope.$state = $state;
    $rootScope.$stateParams = $stateParams;
    $rootScope.globalState = appGlobalState;
    $rootScope.$log = $log; // print to console from template

    function onErrorRequest(rsp) {
      switch (rsp.status) {
        case 401:
          if ($state.next.name !== 'signin' && !$state.includes('signin')) {
            $state.go('signin', {returnState: $state.next.name, returnParams: $state.toParams});
          }
          break;
        case 500:
        case 501:
        case 502:
          $state.go('error');
          break;
        default:
          console.log(rsp);
      }
    }

    Restangular.configuration.getIdFromElem = function (elem) {
      if (typeof elem[elem.route + '_id'] !== 'undefined') {
        return elem[elem.route + '_id'];
      }
      return elem.id;
    };

    Restangular.setBaseUrl(CONST.api);
    Restangular.setErrorInterceptor(onErrorRequest);

    Restangular.setOneBaseUrl = function (newBaseUrl) {
      if (newBaseUrl) {
        var oldBaseUrl = Restangular.configuration.baseUrl;
        Restangular.setBaseUrl(newBaseUrl);
        $timeout(function () {
          Restangular.setBaseUrl(oldBaseUrl);
        });
      }
      return Restangular;
    };

    Restangular.withNoneSuffixConfig = function () {
      return Restangular.withConfig(function (c) {
        c.setRequestSuffix('');
      });
    };

    Restangular.sync = function (fromElement, toElement) {
      Object.keys(fromElement).forEach(key => {
        if (!_.isFunction(fromElement[key])) {
          if (_.isObject(fromElement[key])) {
            if (typeof toElement[key] === 'undefined') {
              toElement[key] = {};
            }
            Restangular.sync(fromElement[key], toElement[key]);
          } else {
            toElement[key] = fromElement[key];
          }
        }
      });
    };

    Restangular.addRequestInterceptor(function (el) {
      cfpLoadingBar.start();
      return el;
    });
    appLocale.getLocale().then(function (locale) {
      Restangular.addFullRequestInterceptor(function (el) {
        return {
          headers: {
            'Accept-Language': locale
          },
          element: el
        };
      });
    });

    if ($location.host() === 'localhost' || $location.host() === '127.0.0.1') {
      Raven.uninstall();
    }
  });
