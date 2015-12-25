const dependencies = [
  require('./FlavorsDetailsParamsCtrl').default.name
];

export default angular.module('boss.admin.flavors.params', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('flavors.details.params', {
        url: '/params',
        views: {
          'detail': {
            template: require('./flavors.details.params.tpl.html'),
            controller: 'FlavorsDetailsParamsCtrl'
          }
        }
      });
  });
