const dependencies = [
  require('../../lib/serviceService/serviceService').default.name,
  require('./details/services.params').default.name,
  require('./details/services.tariffs').default.name,
  require('./new/services.new').default.name
];

const detailsEmptyTpl = require('../details/details.empty.tpl.html');
const detailsTpl = require('../details/details.tpl.html');

export default angular.module('boss.admin.services', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('services', {
        parent: 'boss',
        url: '/services?text&visibility&category&page',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'ServicesCtrl',
            template: require('./services.tpl.html')
          }
        },
        data: {
          pageTitle: 'Services'
        },
        resolve: {
          services: function (serviceService, $stateParams, CONST) {
            var params = angular.extend({limit: CONST.pageLimit}, $stateParams);
            if ($stateParams.category === undefined) {
              angular.extend(params, {category: 'net,storage,custom'});
            }
            return serviceService.list(params);
          },
          categories: function (serviceService) {
            return serviceService.categoriesList()
              .then(rsp => {
                return _.filter(rsp, cat => {
                  return cat.category_id !== 'vm';
                });
              });
          }
        }
      })
      .state('services.details', {
        url: '/{id}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controller: 'ServicesDetailsCtrl'
          }
        },
        resolve: {
          service: function ($stateParams, services) {
            const service = _.find(services, function (obj) {
              if (obj.service_id.toString() == $stateParams.id) {
                return obj;
              }
            });
            $stateParams.isEmpty = !service;
            return service;
          },
          measures: function (serviceService) {
            return serviceService.measures();
          }
        },
        data: {
          detailsVisible: true
        }
      });
  })
  .controller('ServicesCtrl', function ($scope, services, $filter, categories) {
    $scope.pages = Math.ceil(parseInt(services.total) / parseInt(services.perPage));
    $scope.data = services;
    $scope.categories = categories;
    $scope.columns = [
      {title: $filter('translate')('Name'), filter: 'localizedName'},
      {field: 'category', title: $filter('translate')('Category'), filter: 'localizedName', width: 280},
      {field: 'measure', title: $filter('translate')('Units of measurement'), filter: 'localizedName', width: 190},
      {
        field: 'description', title: $filter('translate')('Description'),
        value: function (item) {
          return $filter('localizedName')(item, 'description');
        }
      }
    ];
    $scope.searchTags = [];
    $scope.filters = [
      {
        property: 'visibility', title: $filter('translate')('Status'), options: [
        {text: $filter('translate')('Active'), val: 'visible'},
        {text: $filter('translate')('In archive'), val: 'deleted'}
      ]
      }
    ];
    var categoryFilter = {
      property: 'category', title: $filter('translate')('Categories'), options: []
    };
    categoryFilter.options = categories.map(cat => {
      return {text: $filter('localizedName')(cat), val: cat.category_id};
    });
    $scope.filters.push(categoryFilter);
  })
  .controller('ServicesDetailsCtrl', function ($scope, $controller, $filter, service) {
    $scope.defaultState = 'services.details.params';
    $scope.thisState = 'services.details';
    if (service) {
      angular.extend(this, $controller('DetailsBaseCtrl', {$scope: $scope}));
    }

    $scope.tabs = [
      {link: 'services.details.params', title: $filter('translate')('Parameters')},
      {link: 'services.details.tariffs', title: $filter('translate')('Plans with this Service')}
    ];
  });
