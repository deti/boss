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

import '../vendor/angular-ui-bootstrap/src/position/position';
import '../vendor/angular-ui-bootstrap/src/dropdown/dropdown';
import '../vendor/angular-ui-bootstrap/src/modal/modal';

import '!ngtemplate?relativeTo=angular-ui-bootstrap/!html!../vendor/angular-ui-bootstrap/template/modal/backdrop.html';
import '!ngtemplate?relativeTo=angular-ui-bootstrap/!html!../vendor/angular-ui-bootstrap/template/modal/window.html';

export default [
  'restangular',
  'ngLocale',
  'ngCookies',
  'ipCookie',
  'ui.router',
  'pascalprecht.translate',
  'ngRaven',
  'smart-table',
  'perfect_scrollbar',
  'toaster',
  'tmh.dynamicLocale',
  'angulartics.google.analytics',
  'mgcrea.ngStrap.datepicker',
  'ui.bootstrap.dropdown',
  'angular-loading-bar',
  'ngTagsInput',
  'ngClipboard'
];
