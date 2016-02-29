const dependencies = [
  'restangular',
  'ui.router',
  'angular-loading-bar',
  require('./const/const').default.name,
  require('../../shared/appLocale/appLocale').default.name
];

export default angular.module('skyline.run', dependencies)
  .run(function (CONST, $rootScope, $state, $stateParams, $window, $timeout, $log, Restangular, cfpLoadingBar, appLocale, $location) {
    $rootScope.CONST = CONST;
    $rootScope.$state = $state;
    $rootScope.$stateParams = $stateParams;
    $rootScope.$log = $log; // print to console from template
    $rootScope.CurrentUser = {};

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

    if ($location.host() === 'localhost' || $location.host() === '127.0.0.1') {
      Raven.uninstall();
    }
  });
