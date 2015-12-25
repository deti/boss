module.exports = {
  server_port: 5000,
  build_dir: 'build',
  compile_dir: 'bin',
  compile_with_source_maps: true,
  app_files: {
    js: ['src/app/**/*.js', '!**/*.spec.js'],
    less: ['src/less/**/*.less', '../shared/**/*.less'],
    templates: ['../../common/**/*.tpl.html', 'src/app/**/*.tpl.html', 'src/common/**/*.tpl.html'],
    assets: ['../../common/assets/**/*', 'src/assets/**/*'],
    html: ['src/index.html']
  },
  shared_modules: [
    'bsHasError',
    'bsServerValidate',
    'bsValidateHint',
    'bsFormSendOnce',
    'leadingZerosFilter',
    'localizedNameFilter',
    'localStorage',
    'appLocale',
    'appGlobalState',
    'popupErrorService',
    'leadingZerosFilter',
    'passwordGenerator',
    'trustFilter',
    'bsDynamicName',
    'pickFilter',
    'bsCompileTemplate',
    'bsTable',
    'dialog',
    'bytesFilter',
    'bsEndWith',
    'bsDomainName',
    'urlParser',
    'pollService',
    'openstackService',
    'bsCopyToClipboard',
    'skyline'
  ],
  vendor_files: {
    js: [
      'lodash/lodash.js',
      'moment/min/moment.min.js',
      'jquery/dist/jquery.js',
      'angular/angular.js',
      'angular-ui-router/release/angular-ui-router.js',
      'angular-animate/angular-animate.js',
      'restangular/dist/restangular.js',
      'angular-cookie/angular-cookie.js',
      'angular-translate/angular-translate.js',
      'angular-translate-handler-log/angular-translate-handler-log.js',
      'angular-translate-loader-static-files/angular-translate-loader-static-files.js',
      'angular-translate-storage-local/angular-translate-storage-local.js',
      'angular-translate-storage-cookie/angular-translate-storage-cookie.js',
      'angular-cookies/angular-cookies.js',
      'angular-ui-bootstrap/src/position/position.js',
      'angular-ui-bootstrap/src/dropdown/dropdown.js',
      'raven-js/dist/raven.js',
      'raven-js/plugins/angular.js',
      'angular-smart-table/dist/smart-table.js',
      'angular-dynamic-locale/src/tmhDynamicLocale.js',
      'angulartics/src/angulartics.js',
      'angulartics/src/angulartics-ga.js',
      'angular-loading-bar/build/loading-bar.js',
      'perfect-scrollbar/src/perfect-scrollbar.js',
      'angular-ui-bootstrap/src/modal/modal.js',
      'angular-perfect-scrollbar/src/angular-perfect-scrollbar.js',
      'angularjs-toaster/toaster.js',
      'angular-strap/dist/modules/dimensions.js',
      'angular-strap/dist/modules/tooltip.js',
      'angular-strap/dist/modules/tooltip.tpl.min.js',
      'angular-click-outside/clickoutside.directive.js',
      'zeroclipboard/dist/ZeroClipboard.js',
      'ng-clip/src/ngClip.js'
    ],
    templates: {
      'angular-ui-bootstrap': [
        'template/modal/backdrop.html',
        'template/modal/window.html'
      ]
    },
    assets: [
      'bootstrap/fonts/*',
      'font-awesome/fonts/*',
      'angular-i18n/angular-locale_en-us.js',
      'angular-i18n/angular-locale_ru-ru.js',
      'zeroclipboard/dist/ZeroClipboard.swf'
    ],
    tests: [
      'vendor/angular-mocks/angular-mocks.js'
    ]
  },
  test_files: {
    js: [
      'src/**/*.spec.js'
    ]
  },
  autoprefixer: {
    browsers: ['last 2 versions', 'ie 10']
  },
  backendUrl: {
    dev: 'https://dev.boss.asdco.ru',
    prod: 'https://os.cloudpro.ru'
  },
  proxyRoutes: [
    '/keystone',
    '/nova',
    '/cinder',
    '/neutron',
    '/glance',
    '/mistral',
    '/designate'
  ]
};
