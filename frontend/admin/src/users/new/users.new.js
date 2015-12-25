const dependencies = [
  require('./UsersNewCtrl').default.name
];

export default angular.module('boss.admin.users.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('users.new', {
        url: '/new',
        views: {
          'details@boss': {
            template: require('./users.new.tpl.html'),
            controller: 'UsersNewCtrl'
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'New user'
        }
      });
  });
