const dependencies = [
  'angular-loading-bar',
  'toaster',
  require('../../../lib/customerService/customerService').default.name,
  require('../../../lib/tariffService/tariffService').default.name
];

export default angular.module('boss.admin.customer.tariff_history', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.tariff_history', {
        url: '/tariff_history?after?before',
        views: {
          'detail': {
            template: require('./customer.tariff_history.tpl.html'),
            controller: 'MainDetailsTariffHistoryCtrl'
          }
        },
        resolve: {
          tariffs: function (tariffService) {
            return tariffService.getFullList({visibility: 'all'});
          },
          history: function (customerService, customer, $stateParams) {
            return customerService.getHistory(customer.customer_id, {
              after: $stateParams.after,
              before: $stateParams.before
            })
              .then(function (history) {
                return history
                  .filter(item => item.event === 'tariff')
                  .filter((item, index, array) => {
                    if (index === 0) {
                      return true;
                    }
                    return array[index - 1].snapshot.tariff_id !== item.snapshot.tariff_id;
                  });
              });
          }
        }
      });
  })
  .controller('MainDetailsTariffHistoryCtrl', function ($scope, history, tariffs, $filter) {
    $scope.history = history.map(item => {
      item.localized_name = _.findWhere(tariffs, {tariff_id: item.snapshot.tariff_id}).localized_name;
      item.id = _.uniqueId();
      return item;
    });
  });
