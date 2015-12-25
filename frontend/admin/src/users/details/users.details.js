const dependencies = [
  require('./UsersDetailsCtrl').default.name
];

const detailsEmptyTpl = require('../../details/details.empty.tpl.html');
const detailsTpl = require('./users.details.tpl.html');

export default angular.module('boss.admin.users.details', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('users.details', {
        url: '/{id:[0-9]*}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controllerProvider: function ($stateParams) {
              if ($stateParams.isEmpty) {
                return function () {
                };
              } else {
                return 'UsersDetailsCtrl';
              }
            }
          }
        },
        data: {
          detailsVisible: true
        },
        resolve: {
          user: function (usersData, $stateParams) {
            const user = _.findWhere(usersData, {user_id: parseInt($stateParams.id)});
            $stateParams.isEmpty = !user;
            return user;
          }
        }
      });
  });
