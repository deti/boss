const dependencies = [
  require('./details/customer.actions').default.name,
  require('./details/customer.bill').default.name,
  require('./details/customer.events').default.name,
  require('./details/customer.history').default.name,
  require('./details/customer.info').default.name,
  require('./details/customer.invoice').default.name,
  require('./details/customer.quota').default.name,
  require('./details/customer.report').default.name,
  require('./details/customer.tariff').default.name,
  require('./details/customer.tariff_history').default.name,
  require('./new/customer.new').default.name,
  require('../../lib/tariffService/tariffService').default.name,
  require('../../lib/customerService/customerService').default.name
];

const detailsEmptyTpl = require('../details/details.empty.tpl.html');
const detailsTpl = require('../details/details.tpl.html');

export default angular.module('boss.admin.customer', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('main', {
        parent: 'boss',
        url: '/index?visibility&blocked&customer_mode&customer_type&tariff_ids&text&page',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'MainCtrl',
            template: require('./customers.tpl.html')
          }
        },
        data: {
          pageTitle: 'Customers'
        },
        resolve: {
          tariffs: function (tariffService) {
            return tariffService.getList();
          },
          customersData: function (customerService, tariffs, $stateParams) {
            return customerService.getCustomers(angular.extend({}, {limit: 50}, $stateParams))
              .then(function (items) {
                items.map((item) => {
                  item.tariffInfo = _.findWhere(tariffs, {tariff_id: item.tariff_id});
                  item.balance = 0;
                  return item;
                });
                return items;
              });
          }
        }
      })
      .state('main.details', {
        url: '/{id:[0-9]*}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controller: 'MainDetailsCtrl'
          }
        },
        data: {
          detailsVisible: true
        },
        resolve: {
          customer: function (customersData, Restangular, $stateParams) {
            var customer = _.findWhere(customersData, {customer_id: parseInt($stateParams.id)});
            $stateParams.isEmpty = !customer;
            return customer;
          }
        }
      });
  })
  .controller('MainCtrl', function ($scope, customersData, $state, $rootScope, tariffs, $filter, $stateParams, reportService, appLocale, popupErrorService, cfpLoadingBar) {
    $scope.pages = Math.ceil(parseInt(customersData.total) / parseInt(customersData.perPage));
    $scope.showFilters = false;
    $scope.customers = customersData;
    $scope.textSearch = $stateParams.text;
    $scope.showDownloadPopover = false;
    $scope.btnScrolled = false;

    $scope.downloadReceipts = function () {
      cfpLoadingBar.start();
      reportService.downloadReceipts($scope.startDate, $scope.endDate, appLocale.getBackendLocale(true))
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          popupErrorService.show(e);
          cfpLoadingBar.complete();
        });
    };
    $scope.downloadUsage = function () {
      cfpLoadingBar.start();
      reportService.downloadUsage($scope.startDate, $scope.endDate, appLocale.getBackendLocale(true))
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          popupErrorService.show(e);
          cfpLoadingBar.complete();
        });
    };
    $scope.toggleDownloadPopover = function () {
      if (!$state.is('main')) {
        $state.go('main');
      }
      $scope.showDownloadPopover = !$scope.showDownloadPopover;
    };
    $scope.columns = [
      {field: 'email', title: $filter('translate')('User account')},
      {field: 'detailed_info.name', title: $filter('translate')('Name')},
      {
        field: 'tariff_id', title: $filter('translate')('Plan'), filter: 'localizedName', value: function (item) {
        return _.findWhere(tariffs, {tariff_id: item.tariff_id});
      }
      },
      {
        field: 'account.RUB.current', title: $filter('translate')('Balance'), value: function (item) {
        if (item.account[item.currency]) {
          return $filter('money')(item.account[item.currency].current, item.currency);
        } else {
          return $filter('translate')('No account');
        }
      }
      },
      {
        field: 'created',
        title: $filter('translate')('Created'),
        filter: {name: 'date', args: ['short']},
        reverse: true
      },
      {
        field: 'customer_mode', title: $filter('translate')('Mode'), value: function (item) {
        var modes = {
          test: 'Trial mode',
          pending_prod: 'Transient mode',
          production: 'Working mode'
        };
        return (modes[item.customer_mode] ? $filter('translate')(modes[item.customer_mode]) : '');
      }
      }
    ];

    $scope.filters = [
      {
        property: 'visibility', title: $filter('translate')('Status'), options: [
        {text: $filter('translate')('Active'), val: 'visible'},
        {text: $filter('translate')('In archive'), val: 'deleted'}
      ]
      },
      {
        property: 'blocked', title: $filter('translate')('Lock'), options: [
        {text: $filter('translate')('Not locked'), val: 'false'},
        {text: $filter('translate')('Locked'), val: 'true'}
      ]
      },
      {
        property: 'customer_mode', title: $filter('translate')('Type'), options: [
        {text: $filter('translate')('Trial mode'), val: 'test'},
        {text: $filter('translate')('Working mode'), val: 'production'},
        {text: $filter('translate')('Transient mode'), val: 'pending_prod'}
      ]
      },
      {
        property: 'customer_type', title: $filter('translate')('Customer type'), options: [
        {text: $filter('translate')('Private person'), val: 'private'},
        {text: $filter('translate')('Legal entity'), val: 'entity'}
      ]
      }
    ];
    var tariffFilter = {
      property: 'tariff_ids', title: $filter('translate')('Plans'), options: []
    };
    tariffFilter.options = tariffs.map(tariff => {
      return {text: $filter('localizedName')(tariff), val: tariff.tariff_id};
    });
    $scope.filters.push(tariffFilter);
    $scope.searchTags = [];
  })
  .controller('MainDetailsCtrl', function ($scope, $controller, $filter, customer) {
    $scope.manyTabs = true;
    $scope.defaultState = 'main.details.info';
    $scope.thisState = 'main.details';
    $scope.tabs = [
      {link: 'main.details.actions', title: $filter('translate')('Actions')},
      {link: 'main.details.info', title: $filter('translate')('Information')},
      {link: 'main.details.bill', title: $filter('translate')('Balance')},
      {link: 'main.details.history', title: $filter('translate')('Transactions')},
      {link: 'main.details.events', title: $filter('translate')('Notifications')},
      {link: 'main.details.report', title: $filter('translate')('Report')},
      {link: 'main.details.tariff', title: $filter('translate')('Plan')},
      {link: 'main.details.tariff_history', title: $filter('translate')('Plan history')},
      {link: 'main.details.quota', title: $filter('translate')('Resource quotas')}
    ];
    if (customer) {
      angular.extend(this, $controller('DetailsBaseCtrl', {$scope: $scope}));
      if (customer.customer_type === 'entity') {
        $scope.tabs.push({link: 'main.details.invoice', title: $filter('translate')('Invoice generation')});
      }
    }
  });
