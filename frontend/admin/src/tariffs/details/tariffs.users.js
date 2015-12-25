const dependencies = [];

export default angular.module('boss.admin.tariffs.users', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.details.users', {
        url: '/users',
        views: {
          'detail': {
            template: require('./tariffs.users.tpl.html'),
            controller: 'TariffsDetailsUsersCtrl'
          }
        }
      });
  })
  .controller('TariffsDetailsUsersCtrl', function ($scope, $stateParams, tariffsData) {
    $scope.params = _.findWhere(tariffsData, {tariff_id: parseInt($stateParams.id)});
  });
