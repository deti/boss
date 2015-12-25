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
    $scope.data = history;
    $scope.columns = [
      {
        field: 'date',
        title: $filter('translate')('Date'),
        reverse: true,
        cellClass: 'long-text',
        sortDefault: 'reverse',
        template: "{{::item.date | date:'dd.MM.yy' }}<br>{{::item.date | date:'HH:mm' }}"
      },
      {field: 'user.name', title: $filter('translate')('Name')},
      {field: 'delta', title: $filter('translate')('Sum'), template: '<span ng-bind-html="item.delta| money:item.currency | trust"></span>'},
      {field: 'comment', title: $filter('translate')('Comment'), cellClass: 'long-text'}
    ];
  });



