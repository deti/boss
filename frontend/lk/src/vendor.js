import 'lodash';
import 'jquery';
import 'angular';
import 'restangular';
import 'angular-ui-router';
import 'angular-translate';
import 'angular-translate-storage-local';
import 'angular-translate-storage-cookie';
import 'angular-cookies';
import 'angular-cookie';
import 'angular-smart-table';
import 'angular-dynamic-locale';
import 'angular-loading-bar';
import 'perfect-scrollbar';
import 'angular-perfect-scrollbar';
import 'angularjs-toaster';
import 'zeroclipboard';
import 'ng-clip';
import 'raven-js/dist/raven.js';
import 'raven-js/plugins/angular.js';
import 'angulartics/src/angulartics';
import 'angulartics/src/angulartics-ga';
import 'ng-tags-input';
import 'angular-strap/dist/modules/dimensions';
import 'angular-strap/dist/modules/tooltip';
import 'angular-strap/dist/modules/tooltip.tpl.min';
import 'angular-strap/dist/modules/date-formatter';
import 'angular-strap/dist/modules/date-parser';
import 'angular-strap/dist/modules/datepicker';
import 'angular-click-outside/clickoutside.directive';
import 'cron-to-text';

import '../vendor/angular-ui-bootstrap/src/position/position';
import '../vendor/angular-ui-bootstrap/src/dropdown/dropdown';
import '../vendor/angular-ui-bootstrap/src/modal/modal';
import '../vendor/angular-ui-bootstrap/src/progressbar/progressbar';
import '!ngtemplate?relativeTo=angular-ui-bootstrap/!html!../vendor/angular-ui-bootstrap/template/modal/backdrop.html';
import '!ngtemplate?relativeTo=angular-ui-bootstrap/!html!../vendor/angular-ui-bootstrap/template/modal/window.html';

export default [
  'restangular',
  'ngLocale',
  'ngCookies',
  'ipCookie',
  'ui.router',
  'ui.bootstrap.dropdown',
  'pascalprecht.translate',
  'ngRaven',
  'smart-table',
  'tmh.dynamicLocale',
  'angulartics.google.analytics',
  'ngTagsInput',
  'angular-loading-bar',
  'perfect_scrollbar',
  'mgcrea.ngStrap.datepicker',
  'toaster',
  'ui.bootstrap.progressbar',
  'ngClipboard'
];
