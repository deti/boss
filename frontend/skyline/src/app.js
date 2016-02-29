import '../less/main.less';
import '../assets/favicon.ico';

import vendorDependencies from './vendor';

const dependencies = [
  // --- directives ---
  require('../../shared/bsHasError/bsHasError').default.name,
  require('../../shared/bsValidateHint/bsValidateHint').default.name,
  require('../../shared/popupErrorService/popupErrorService').default.name,
  require('../../shared/bsServerValidate/bsServerValidate').default.name,
  require('../../shared/bsTable/bsTable').default.name,
  require('../../shared/bsFormSendOnce/bsFormSendOnce').default.name,
  require('../../shared/bsProgressbar/bsProgressbar').default.name,
  require('../../shared/bsEndWith/bsEndWith').default.name,
  require('../../shared/bsCopyToClipboard/bsCopyToClipboard').default.name,
  // --- filters ---
  require('../../shared/localizedNameFilter/localizedNameFilter').default.name,
  require('../../shared/moneyFilter/moneyFilter').default.name,
  require('../../shared/bytesFilter/bytesFilter').default.name,
  require('../../shared/cronToTextFilter/cronToTextFilter').default.name,
  // --- controllers ---
  require('./openstack/openstack').default.name,
  require('./logout/logout').default.name,
  require('./auth/auth').default.name,
  require('../../shared/error/error').default.name,
  // --- application ---
  require('./const/const').default.name,
  require('./config').default.name,
  require('./run').default.name,
  require('./states').default.name
];

angular.module('skyline', vendorDependencies.concat(dependencies))
  .factory('RavenConfig', function () {
    return {
      dsn: 'http://fabb17faa23840a78f84b1a6800678ec@sentry.boss.asdco.ru/2',
      config: {
        tags: {
          app: 'skyline-app',
          release: window.app_version || null
        }
      }
    };
  })
  .controller('LayoutCtrl', function ($scope, $window) {
    var $win = angular.element($window);
    $win.on('resize', _.throttle(function () {
      $scope.windowHeight = $win.height();
      $scope.$apply();
    }, 100));
  })
  .controller('BossCtrl', function ($scope, $controller) {
    angular.extend(this, $controller('LayoutCtrl', {$scope: $scope}));
  })
  .controller('AppCtrl', function AppCtrl($rootScope, $state, $scope, $filter, tmhDynamicLocale, cfpLoadingBar, CONST) {
    $rootScope.$on('$stateChangeStart', cfpLoadingBar.start);
    $rootScope.$on('$stateChangeSuccess', cfpLoadingBar.complete);
    $rootScope.$on('$stateChangeError', cfpLoadingBar.complete);
    var lastError = 0;
    $rootScope.$on('$stateChangeError', function (event, toState, fromState, a, b, error) {
      if (error === 'should log in') {
        $state.go('auth');
        return;
      }
      if (Date.now() - lastError < 500) {
        $state.go('error');
      }
      lastError = Date.now();
      console.error(`Error on state change to ${toState.name}`, error);
    });
    $rootScope.$on('$stateChangeStart', function (evt, toState, toParams) {
      toState.stringifyBack = encodeURIComponent(angular.toJson({name: toState.name, params: toParams}));
    });

    $scope.$on('$stateChangeSuccess', function (evt, toState) {
      if (angular.isDefined(toState.data)) {
        if (angular.isDefined(toState.data.pageTitle)) {
          $scope.pageTitle = $filter('translate')(toState.data.pageTitle) + ' - Skyline';
        }
        $scope.htmlClassname = angular.isDefined(toState.data.htmlClassname) ? toState.data.htmlClassname : '';
        $scope.bodyClassname = angular.isDefined(toState.data.bodyClassname) ? toState.data.bodyClassname : '';
        if (CONST.red_stars) {
          $scope.htmlClassname += ' g-red-stars';
        }
      }
    });
  });
