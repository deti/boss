const dependencies = [
  require('./header/header').default.name,
  require('./sidemenu/sidemenu').default.name,
  require('./const/const').default.name
];

export default angular.module('skyline.states', dependencies)
  .config(function ($stateProvider, $translateProvider, $urlRouterProvider, CONST) {
    $stateProvider.state('boss-base', {
      abstract: true,
      url: `/${CONST.relativePath}`
    });

    $stateProvider.state('boss-base-resolve', {
      abstract: true,
      parent: 'boss-base',
      resolve: {
        locale: function (appLocale) {
          return appLocale.load();
        }
      }
    });
    $stateProvider.state('boss-clean', {
      abstract: true,
      parent: 'boss-base-resolve',
      views: {
        'header@boss-clean': {
          template: require('./header/header-col-1.tpl.html'),
          controller: 'HeaderCtrl'
        },
        'layout@': {
          template: require('./layouts/col-1.tpl.html'),
          controller: 'LayoutCtrl'
        }
      }
    });
    $stateProvider.state('boss-root', {
      url: '',
      parent: 'boss-base-resolve',
      views: {
        'layout@': {
          template: '',
          controller: function ($state) {
            console.log('root state');
            $state.go('openstack');
          }
        }
      },
      resolve: {}
    });
    $stateProvider.state('boss', {
      abstract: true,
      parent: 'boss-root',
      views: {
        'header@boss': {
          template: require('./header/header.tpl.html'),
          controller: 'HeaderCtrl'
        },
        'layout@': {
          template: require('./layouts/col-2.tpl.html'),
          controller: 'BossCtrl'
        },
        'sidemenu@boss': {
          template: require('./sidemenu/sidemenu.tpl.html'),
          controller: 'SidemenuCtrl'
        }
      }
    });
    $urlRouterProvider.otherwise(`/${CONST.relativePath}`);
  });
