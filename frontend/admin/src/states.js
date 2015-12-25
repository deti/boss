const dependencies = [
  require('./header/header').default.name,
  require('./sidemenu/sidemenu').default.name,
  require('./layouts/LayoutCtrl').default.name,
  require('../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.admin.states', dependencies)
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
          template: require('./layouts/col-1.tpl.html')
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
        userInfo: function (currentUserService) {
          return currentUserService.userInfo()
            .then(function (currentUser) {
              Raven.setUserContext({
                email: currentUser.email || null,
                id: currentUser.user_id || null,
                role: currentUser.role.role_id || null
              });
              return currentUser;
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
          controller: 'LayoutCtrl'
        },
        'sidemenu@boss': {
          template: require('./sidemenu/sidemenu.tpl.html'),
          controller: 'SideMenuCtrl'
        }
      }
    });
    $urlRouterProvider.otherwise(`/${CONST.relativePath}`);
  });
