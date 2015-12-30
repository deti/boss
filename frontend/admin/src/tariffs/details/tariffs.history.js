const dependencies = [
  require('../../../lib/tariffService/tariffService').default.name
];

export default angular.module('boss.admin.tariffs.history', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.details.history', {
        url: '/history?after?before',
        views: {
          'detail': {
            template: require('./tariffs.history.tpl.html'),
            controller: 'TariffsDetailsHistoryCtrl'
          }
        },
        resolve: {
          history: function (tariff, tariffService, $stateParams) {
            return tariffService.history(tariff.tariff_id, {
              tariff: tariff.tariff_id,
              date_after: $stateParams.after,
              date_before: $stateParams.before
            });
          }
        },
        data: {
        }
      });
  })
  .controller('TariffsDetailsHistoryCtrl', function ($scope, history, $filter) {
    $scope.customDetailsHeader.tpl = null;
    $scope.gridConfig = {
      data: history,
      uniqueField: 'history_id',
      columns: [
        {
          field: 'date',
          sortDefault: 'reverse',
          title: $filter('translate')('Date'),
          filter: 'date',
          reverse: true
        },
        {field: 'user.name', title: $filter('translate')('Name')},
        {filter: 'localizedName', cellClass: 'long-text', title: $filter('translate')('Action')}
      ]
    };
  });
