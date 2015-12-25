const dependencies = [
  require('../../lib/userService/userService').default.name,
  require('./TransactionsCtrl').default.name
];

export default angular.module('boss.lk.transactions', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('transactions', {
      parent: 'boss',
      url: '/transactions?after?before',
      views: {
        'main@boss': {
          controller: 'TransactionsCtrl',
          template: require('./transactions.tpl.html')
        }
      },
      resolve: {
        balanceHistory: function ($stateParams, userService) {
          return userService.balanceHistory({after: $stateParams.after, before: $stateParams.before});
        }
      },
      data: {
        pageTitle: 'Transactions'
      }
    });
  });
