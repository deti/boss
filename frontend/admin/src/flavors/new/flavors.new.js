const dependencies = [
  require('../../../lib/serviceService/serviceService').default.name,
  require('./FlavorsNewCtrl').default.name
];

export default angular.module('boss.admin.flavors.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('flavors.new', {
        url: '/new/',
        views: {
          'details@boss': {
            template: require('./flavors.new.tpl.html'),
            controller: 'FlavorsNewCtrl'
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'New template'
        },
        resolve: {
          measures: function (serviceService) {
            return serviceService.measures({measure_type: 'time'});
          }
        }
      });
  });
