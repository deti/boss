const dependencies = [
  'ui.router',
  'boss.const',
  require('./header/header').default.name,
  require('./sidemenu/sidemenu').default.name
];

export default angular.module('boss.lk.states', dependencies)
  .config(function ($stateProvider, $urlRouterProvider, CONST) {
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
        },
        langList: function (utilityService) {
          return utilityService.activeLanguages();
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
      },
      resolve: {
        userInfo: function () {
          return {};
        }
      }
    });
    $stateProvider.state('boss-root', {
      url: '',
      parent: 'boss-base-resolve',
      views: {
        'layout@': {
          template: '',
          controller: function ($state, userInfo) {
            if (userInfo) {
              $state.go('main');
            }
          }
        }
      },
      resolve: {
        userInfo: function (userService) {
          return userService.userInfo()
            .then(function (userInfo) {
              Raven.setUserContext({
                email: userInfo.email || null,
                id: userInfo.customer_id || null
              });
              return userInfo;
            })
            .catch(function (e) {
            });
        }
      }
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
