import '../less/main.less';
import '../assets/favicon.ico';

import vendorDependencies from './vendor';

const dependencies = [
  require('../lib/userService/userService').default.name,
  // --- directives ---
  require('../../shared/bsHasError/bsHasError').default.name,
  require('../../shared/bsValidateHint/bsValidateHint').default.name,
  require('../../shared/popupErrorService/popupErrorService').default.name,
  require('../../shared/bsServerValidate/bsServerValidate').default.name,
  require('../../shared/bsDateRangePicker/bsDateRangePicker').default.name,
  require('../../shared/bsDateRange/bsDateRange').default.name,
  require('../../shared/bsTable/bsTable').default.name,
  require('../../shared/bsPhoneInput/bsPhoneInput').default.name,
  require('../../shared/bsDropdownButton/bsDropdownButton').default.name,
  require('../../shared/bsDynamicName/bsDynamicName').default.name,
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
  require('./authorization/authorization').default.name,
  require('./main/main').default.name,
  require('./setPassword/setPassword').default.name,
  require('./restorePassword/restorePassword').default.name,
  require('./signout/signout').default.name,
  require('./signup/signup').default.name,
  require('./signupFinished/signupFinished').default.name,
  require('./confirmation/confirmation').default.name,
  require('./transactions/transactions').default.name,
  require('./support/support').default.name,
  require('./services/services').default.name,
  require('./news/news').default.name,
  require('./settings/settings').default.name,
  require('./horizon/horizon').default.name,
  require('./statistics/statistics').default.name,
  require('./production/production').default.name,
  require('./production/production.step2').default.name,
  require('./pay/pay').default.name,
  require('./cards/cards').default.name,
  require('./openstack/openstack').default.name,
  require('../../shared/error/error').default.name,
  // --- application ---
  require('./const/const').default.name,
  require('./config').default.name,
  require('./run').default.name,
  require('./states').default.name
];

angular.module('boss.lk', vendorDependencies.concat(dependencies))
  .factory('RavenConfig', function (CONST) {
    return {
      dsn: CONST.local.sentry,
      config: {
        tags: {
          app: 'lk-app',
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
  .controller('BossCtrl', function ($scope, $controller, userInfo, pollService, userService) {
    angular.extend(this, $controller('LayoutCtrl', {$scope: $scope}));
    $scope.userInfo = userInfo;
    var promise = pollService.startPolling(function () {
      return userService.userInfo(true);
    }, userInfo, 5 * 60 * 1000);

    $scope.$on('$destroy', function () {
      promise.stop();
    });
  })
  .controller('AppCtrl', function AppCtrl($rootScope, $scope, $state, $filter, tmhDynamicLocale, cfpLoadingBar, CONST, SKYLINE_EVENTS, userService) {
    var cloudName = ' ' + (CONST.local.provider_info.cloud_name ? CONST.local.provider_info.cloud_name : 'BOSS');

    $rootScope.$on('$stateChangeStart', cfpLoadingBar.start);
    $rootScope.$on('$stateChangeSuccess', cfpLoadingBar.complete);
    $rootScope.$on('$stateChangeError', cfpLoadingBar.complete);
    var lastError = 0;
    $rootScope.$on('$stateChangeError', function (event, toState, fromState, a, b, error) {
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
          $scope.pageTitle = $filter('translate')(toState.data.pageTitle) + ' ' + $filter('translate')('- Personal Account -') + cloudName;
        }
        $scope.htmlClassname = angular.isDefined(toState.data.htmlClassname) ? toState.data.htmlClassname : '';
        $scope.bodyClassname = angular.isDefined(toState.data.bodyClassname) ? toState.data.bodyClassname : '';
        if (CONST.local.skyline.red_stars) {
          $scope.htmlClassname += ' g-red-stars';
        }
      }
    });

    function updateUsedQuotas() {
      userService.usedQuotas(true); // we don't interesting in result, because it will still be cached. But in next request we will get new results
      // TODO: check that quotas really updated, look at "ago" property of response
    }

    Object.keys(SKYLINE_EVENTS).forEach(key => {
      $rootScope.$on(SKYLINE_EVENTS[key], updateUsedQuotas);
    });
  });
