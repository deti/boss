const dependencies = [
  require('../../lib/userService/userService').default.name,
  require('./details/users.details').default.name,
  require('./new/users.new').default.name,
  require('./UsersCtrl').default.name
];

export default angular.module('boss.admin.users', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('users', {
        parent: 'boss',
        url: '/users?role&text&visibility&page',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'UsersCtrl',
            template: require('./users.tpl.html')
          }
        },
        data: {
          pageTitle: 'Users'
        },
        resolve: {
          usersData: function (userService, $stateParams) {
            return userService.getList(angular.extend({}, {limit: 50}, $stateParams));
          },
          userRoles: function (utilityService) {
            return utilityService.roles();
          }
        }
      });
  });
