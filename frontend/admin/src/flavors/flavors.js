const dependencies = [
  require('./FlavorsCtrl').default.name,
  require('./FlavorsDetailsCtrl').default.name,
  require('./new/flavors.new').default.name,
  require('./params/flavors.params').default.name,
  require('./tariffs/flavors.tariffs').default.name,
  require('../../lib/serviceService/serviceService').default.name
];

const detailsEmptyTpl = require('../details/details.empty.tpl.html');
const detailsTpl = require('../details/details.tpl.html');

export default angular.module('boss.admin.flavors', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('flavors', {
        parent: 'boss',
        url: '/flavors?text&visibility&page',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'FlavorsCtrl',
            template: require('./flavors.tpl.html')
          }
        },
        data: {
          pageTitle: 'VM Templates'
        },
        resolve: {
          flavors: function (serviceService, $stateParams, CONST) {
            return serviceService.list(angular.extend({}, {limit: CONST.limit, category: 'vm'}, $stateParams));
          }
        }
      })
      .state('flavors.details', {
        url: '/{id}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controller: 'FlavorsDetailsCtrl'
          }
        },
        resolve: {
          flavor: function ($stateParams, flavors) {
            const flavor = _.findWhere(flavors, {service_id: parseInt($stateParams.id)});
            $stateParams.isEmpty = !flavor;
            return flavor;
          }
        },
        data: {
          detailsVisible: true
        }
      });
  });
