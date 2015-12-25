const dependencies = [];

export default angular.module('boss.lk.TransactionsCtrl', dependencies)
  .controller('TransactionsCtrl', function TransactionsCtrl($scope, $filter, balanceHistory) {
    $scope.balanceHistory = balanceHistory;
    $scope.columns = [
      {
        field: 'date',
        sortDefault: 'reverse',
        reverse: true,
        filter: {name: 'date', args: ['short']},
        title: $filter('translate')('Date'),
        width: 200
      },
      {
        field: 'delta',
        template: '<span ng-bind-html="item.delta | money: item.currency | trust"></span>',
        title: $filter('translate')('Amount'),
        width: 200
      },
      {
        field: 'comment',
        title: $filter('translate')('Description')
      }
    ];
  });
