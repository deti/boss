const dependencies = [
  'restangular',
  require('../../../lib/customerService/customerService').default.name
];

export default angular.module('boss.admin.customer.history', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.history', {
        url: '/history?after?before',
        views: {
          'detail': {
            template: require('./customer.history.tpl.html'),
            controller: 'MainDetailsHistoryCtrl'
          }
        },
        resolve: {
          history: function ($stateParams, $location, customerService, customer) {
            return customerService.getBalanceHistory(customer.customer_id, {
              after: $stateParams.after,
              before: $stateParams.before
            });
          }
        },
        data: {
        }
      });
  })
  .controller('MainDetailsHistoryCtrl', function ($scope, history, $filter) {
    $scope.gridConfig = {
      data: history,
      columns: [
        {
          title: $filter('translate')('Date'),
          field: 'date',
          filter: {name: 'date', args: ['dd.MM.yy HH:mm']},
          reverse: true,
          sortDefault: true
        },
        {
          title: $filter('translate')('Name'),
          field: 'user.name'
        },
        {
          title: $filter('translate')('Sum'),
          field: 'delta',
          template: '<span ng-bind-html="item.delta| money:item.currency | trust"></span>'},
        {
          title: $filter('translate')('Comment'),
          field: 'comment',
          cellClass: 'long-text'
        }
      ]
    }
  });



