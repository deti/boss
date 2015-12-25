const dependencies = [
  'ui.router',
  'toaster',
  require('../../lib/currencyService/currencyService').default.name,
  require('../../lib/tariffService/tariffService').default.name,
  require('./details/tariffs.clients').default.name,
  require('./details/tariffs.history').default.name,
  require('./details/tariffs.info').default.name,
  require('./details/tariffs.services').default.name,
  require('./details/tariffs.users').default.name,
  require('./new/tariffs.new').default.name
];

const detailsEmptyTpl = require('../details/details.empty.tpl.html');
const detailsTpl = require('../details/details.tpl.html');

export default angular.module('boss.admin.tariffs', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs', {
        parent: 'boss',
        url: '/tariffs?currency&text&visibility&parent&page',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'TariffsCtrl',
            template: require('./tariffs.tpl.html')
          }
        },
        data: {
          pageTitle: 'Plans'
        },
        resolve: {
          tariffsData: function (tariffService, $stateParams, CONST) {
            return tariffService.getList(angular.extend({}, {limit: CONST.pageLimit}, $stateParams));
          },
          activeCurrency: function (currencyService) {
            return currencyService.activeCurrency();
          },
          tariffsFullList: function (tariffService) {
            return tariffService.getFullList({visibility: 'all'});
          }
        }
      })
      .state('tariffs.details', {
        url: '/{id:[0-9]*}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controller: 'TariffsDetailsCtrl'
          }
        },
        resolve: {
          tariff: function (tariffsData, $stateParams) {
            const tariff = _.findWhere(tariffsData, {tariff_id: parseInt($stateParams.id)});
            $stateParams.isEmpty = !tariff;
            return tariff;
          }
        },
        data: {
          detailsVisible: true
        }
      });
  })
  .controller('TariffsCtrl', function ($scope, $filter, tariffsData, tariffsFullList, tariffService, toaster, TARIFF_STATE, activeCurrency) {
    $scope.pages = Math.ceil(parseInt(tariffsData.total) / parseInt(tariffsData.perPage));
    $scope.data = tariffsData;
    $scope.TARIFF_STATE = TARIFF_STATE;
    $scope.columns = [
      {title: $filter('translate')('Name'), filter: 'localizedName'},
      {
        field: 'users',
        title: $filter('translate')('Subscribed customers'),
        template: '<a class="dashed" ui-sref="main({tariff_ids: item.tariff_id})" ng-click="; $event.stopPropagation();">{{item.users}}</a>'
      },
      {field: 'status', title: $filter('translate')('Status'), filter: 'localizedName'},
      {field: 'currency', title: $filter('translate')('Currency'), width: 150},
      {field: 'created', title: $filter('translate')('Created'), filter: {name: 'date', args: ['short']}, width: 180},
      {field: 'modified', title: $filter('translate')('Changed'), filter: {name: 'date', args: ['short']}, width: 180},
      {
        template: '<label class="custom-checkbox"><input type="checkbox" disabled ng-model="item.default"/><span class="checkbox-elem"></span></label>',
        titleClass: 'flag',
        width: '70'
      }
    ];
    $scope.searchTags = [];
    var currencyFilter = {
      property: 'currency', title: $filter('translate')('Currency'), options: []
    };
    currencyFilter.options = activeCurrency.map(currency => {
      return {text: currency.currency, val: currency.code};
    });
    $scope.filters = [
      currencyFilter,
      {
        property: 'visibility', title: $filter('translate')('Status'), options: [
        {text: $filter('translate')('Active'), val: 'visible'},
        {text: $filter('translate')('In archive'), val: 'deleted'}
      ]
      }
    ];
    var allTariffFilter = {
      property: 'parent', title: $filter('translate')('Basic plan'), options: []
    };
    allTariffFilter.options = tariffsFullList.map(tariff => {
      return {text: $filter('localizedName')(tariff), val: tariff.tariff_id};
    });
    allTariffFilter.options.push({text: $filter('translate')('Without basic plan'), val: 0});
    $scope.filters.push(allTariffFilter);
  })
  .controller('TariffsDetailsCtrl', function ($scope, $filter, $controller, $state, tariff) {
    $scope.defaultState = 'tariffs.details.info';
    $scope.thisState = 'tariffs.details';
    if (tariff) {
      angular.extend(this, $controller('DetailsBaseCtrl', {$scope: $scope}));

      $scope.tabs = [
        {link: 'tariffs.details.info', title: $filter('translate')('Information')},
        {link: 'tariffs.details.services', title: $filter('translate')('Services')},
        {link: 'tariffs.details.history', title: $filter('translate')('History')},
        {title: $filter('translate')('Customers'), state: 'tariffs.details.clients', go: function () {
          $state.go('tariffs.details.clients', {tariff_ids: tariff.tariff_id});
        }}
      ];
    }
  });
