const dependencies = [
  require('../../../lib/serviceService/serviceService').default.name,
  require('./FlavorsDetailsTariffsCtrl').default.name
];

export default angular.module('boss.admin.flavors.tariffs', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('flavors.details.tariffs', {
        url: '/tariffs',
        views: {
          'detail': {
            template: require('./flavors.details.tariffs.tpl.html'),
            controller: 'FlavorsDetailsTariffsCtrl'
          }
        },
        resolve: {
          tariffs: function (serviceService, flavor) {
            return serviceService.tariffsWithService(flavor);
          }
        }
      });
  });
