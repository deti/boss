import '../less/main.less';
import '../assets/favicon.ico';
import vendorDependencies from './vendor';

const dependencies = [
  // --- directives ---
  require('../../shared/bsHasError/bsHasError').default.name,
  require('../../shared/bsValidateHint/bsValidateHint').default.name,
  require('../../shared/popupErrorService/popupErrorService').default.name,
  require('../../shared/bsServerValidate/bsServerValidate').default.name,
  require('../../shared/bsDateRangePicker/bsDateRangePicker').default.name,
  require('../../shared/bsDateRange/bsDateRange').default.name,
  require('../../shared/bsTable/bsTable').default.name,
  require('../../shared/bsMatch/bsMatch').default.name,
  require('../../shared/bsDynamicName/bsDynamicName').default.name,
  require('../../shared/bsPhoneInput/bsPhoneInput').default.name,
  require('../../shared/bsDropdownButton/bsDropdownButton').default.name,
  require('../../shared/bsFormSendOnce/bsFormSendOnce').default.name,
  require('../../shared/bsUnfocusable/bsUnfocusable').default.name,
  require('../lib/bsTableFilter/bsTableFilter').default.name,
  require('../lib/bsTableFilter/bsTableFilterTags').default.name,
  require('../lib/bsTablePagination/bsTablePagination').default.name,
  require('../lib/bsFormSaver/bsFormSaver').default.name,
  require('../lib/bsInfiniteScroll/bsInfiniteScroll').default.name,
  require('../../shared/bsGrid/index').default.name,
  // --- filters ---
  require('../../shared/localizedNameFilter/localizedNameFilter').default.name,
  require('../../shared/leadingZerosFilter/leadingZerosFilter').default.name,
  require('../../shared/moneyFilter/moneyFilter').default.name,
  require('../../shared/bytesFilter/bytesFilter').default.name,
  // --- controllers ---
  require('./details/details').default.name,
  require('./customers/customer').default.name,
  require('./signin/signin').default.name,
  require('./services/services').default.name,
  require('./flavors/flavors').default.name,
  require('./tariffs/tariffs').default.name,
  require('./users/users').default.name,
  require('./news/news').default.name,
  require('./grafana/grafana').default.name,
  require('./openstackUsage/openstackUsage').default.name,
  require('./signout/signout').default.name,
  require('./restorePassword/restorePassword').default.name,
  require('./set-password/set-password').default.name,
  require('./system/system').default.name,
  require('../../shared/skyline/admin/projects').default.name,
  require('./osLogin/osLogin').default.name,
  require('../../shared/error/error').default.name,
  // --- application ---
  require('./const/const').default.name,
  require('./config').default.name,
  require('./states').default.name,
  require('./run').default.name
];

angular.module('boss.admin', vendorDependencies.concat(dependencies))
  .factory('RavenConfig', function (CONST) {
    return {
      dsn: CONST.local.sentry,
      config: {
        tags: {
          app: 'admin-app',
          release: window.app_version || null
        }
      }
    };
  })
  .controller('AppCtrl', function AppCtrl($rootScope, $scope, $state, $filter, tmhDynamicLocale, cfpLoadingBar, appGlobalState, toaster, CONST) {
    var cloudName = ' ' + (CONST.local.provider_info.cloud_name ? CONST.local.provider_info.cloud_name : 'BOSS');

    $rootScope.$on('$stateChangeStart', cfpLoadingBar.start);
    $rootScope.$on('$stateChangeSuccess', cfpLoadingBar.complete);
    $rootScope.$on('$stateChangeError', cfpLoadingBar.complete);

    var lastError = 0;
    $rootScope.$on('$stateChangeError', function (event, toState, toParams, fromState, fromParams, error) {
      if (Date.now() - lastError < 500) {
        $state.go('error');
      }
      lastError = Date.now();
      console.error(`Error on state change to ${toState.name}`, error);
      toaster.pop('error', $filter('translate')('Server error'));
    });
    $scope.$on('$stateChangeSuccess', function (evt, toState) {
      if (angular.isDefined(toState.data)) {
        if (angular.isDefined(toState.data.pageTitle)) {
          $scope.pageTitle = $filter('translate')(toState.data.pageTitle) + ' ' + $filter('translate')('- Administrator panel -') + cloudName;
        }
        $scope.htmlClassname = angular.isDefined(toState.data.htmlClassname) ? toState.data.htmlClassname : '';
        $scope.bodyClassname = angular.isDefined(toState.data.bodyClassname) ? toState.data.bodyClassname : '';
        appGlobalState.detailsVisible = toState.data.detailsVisible;
        appGlobalState.detailsWide = toState.data.detailsWide;
      }
    });
    $scope.globalState = appGlobalState;
  });
