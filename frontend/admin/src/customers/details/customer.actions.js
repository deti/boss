const dependencies = [
  require('./CustomerActionsCtrl').default.name
];

export default angular.module('boss.admin.customer.actions', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.actions', {
        url: '/actions',
        views: {
          'detail': {
            template: require('./customer.actions.tpl.html'),
            controller: 'CustomerActionsCtrl'
          }
        }
      });
  });
