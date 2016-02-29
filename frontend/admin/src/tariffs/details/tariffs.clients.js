const dependencies = [
  'toaster',
  require('../../../lib/tariffService/tariffService').default.name,
  require('../../../lib/customerService/customerService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];

export default angular.module('boss.admin.tariffs.clients', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('tariffs.details.clients', {
        url: '/clients?customer_type&tariff_ids&created_after&created_before',
        views: {
          'details@boss': {
            template: require('../../details/details.no-scroll.tpl.html'),
            controller: 'TariffsDetailsCtrl'
          },
          'detail@tariffs.details.clients': {
            template: require('./tariffs.clients.tpl.html'),
            controller: 'TariffsDetailsClientsCtrl'
          }
        },
        resolve: {
          allTariffs: function (tariffService, CONST) {
            return tariffService.getList({limit: CONST.pageLimit, visibility: 'all'});
          },
          customers: function (tariff, customerService, $stateParams, CONST) {
            var params = {};
            params.customer_type = $stateParams.customer_type;
            params.tariff_ids = $stateParams.tariff_ids;
            params.created_after = $stateParams.created_after;
            params.created_before = $stateParams.created_before;
            return customerService.getCustomers(angular.extend({}, {limit: CONST.pageLimit}, params));
          }
        },
        data: {
          detailsWide: true
        }
      });
  })
  .controller('TariffsDetailsClientsCtrl', function ($scope, $stateParams, customers, $filter, allTariffs, $state, customerService, CONST, toaster, popupErrorService) {
    $scope.allTariffs = allTariffs.plain();
    $scope.customers = customers.plain();

    $scope.tariffsTotal = allTariffs.total;
    $scope.tariffsPerPage = allTariffs.perPage;
    $scope.tariffsCurrentPage = 1;
    $scope.tariffsParams = {visibility: 'all'};

    $scope.customersTotal = customers.total;
    $scope.customersPerPage = customers.perPage;
    $scope.customersCurrentPage = 1;
    $scope.customersParams = {
      customer_type: $stateParams.customer_type,
      tariff_ids: $stateParams.tariff_ids,
      created_after: $stateParams.created_after,
      created_before: $stateParams.created_before
    };
    $scope.hint = $filter('translate')('You can add customers to plan on this page.') +
      '\n\n' +
      $filter('translate')('You can select customers using filters on the left.') +
      '\n\n' +
      $filter('translate')('When you press button \'Add to this plan\', selected customers will be added to the plan.') +
      '\n\n' +
      $filter('translate')('You can deselect customer by clicking on icon before his address.') +
      $filter('translate')('All filtered customers will be marked.');

    $scope.show = {};
    $scope.show.tariffFilter = !!$stateParams.tariff_ids;
    $scope.show.typeFilter = !!$stateParams.customer_type;
    $scope.show.creationFilter = !!($stateParams.created_after || $stateParams.created_before);

    $scope.customerOnElement = function (item) {
      item.selected = true;
    };

    $scope.afterParam = 'created_after';
    $scope.beforeParam = 'created_before';
    $scope.resetTime = true;

    $scope.filters = {};
    $scope.filters.searchQuery = '';
    $scope.filters.searchCount = null;

    function addField(array, field, value) {
      return array.map(item => {
        item[field] = value;
        return item;
      });
    }

    $scope.customers = addField($scope.customers, 'selected', true);
    $scope.allTariffs = addField($scope.allTariffs, 'selected', false);

    function selectTariff(id) {
      var tar = _.find($scope.allTariffs, 'tariff_id', parseInt(id));
      if (tar) {
        tar.selected = true;
      }
    }

    function getFilters() {
      $scope.filters.customerType = $stateParams.customer_type ? $stateParams.customer_type : 'any';

      if ($stateParams.tariff_ids) {
        var tariffIds = $stateParams.tariff_ids.split(',');
        tariffIds.forEach(id => {
          selectTariff(id);
        });
      }
    }

    getFilters();

    $scope.getCustomersData = function () {
      var queue = {}, tariffIds = [];
      if ($scope.filters.customerType === 'any') {
        $scope.filters.customerType = undefined;
      }
      queue.customer_type = $scope.filters.customerType;

      $scope.allTariffs.forEach(tariff => {
        if (tariff.selected) {
          tariffIds.push(tariff.tariff_id);
        }
      });
      queue.tariff_ids = tariffIds.join();
      $state.go($state.current, queue);
    };

    $scope.search = function () {
      if ($scope.filters.searchQuery) {
        if ($scope.filters.searchCount === null) {
          $scope.customers = _.filter($scope.customers, function (customer) {
            return _.includes(customer.email, $scope.filters.searchQuery);
          });
          $scope.filters.searchCount = $scope.customers.length;
        } else {
          $state.reload();
        }
      }
    };

    $scope.check = function (tariff) {
      $scope.getCustomersData();
    };

    $scope.updateCustomersTariff = function () {
      var selectedCustomers = [];
      $scope.customers.forEach(customer => {
        if (customer.selected) {
          selectedCustomers.push(customer.customer_id);
        }
      });

      customerService.setGroupTariff(selectedCustomers, parseInt($stateParams.id))
      .then(function (rsp) {
        toaster.pop('success', $filter('translate')('Plan is successfully changed'));
        $state.go($state.current, {tariff_ids: $stateParams.id,
                                  created_before: undefined,
                                  created_after: undefined,
                                  customer_type: undefined
                                  });
      }, function (err) {
        popupErrorService.show(err);
      });
    };

    $scope.$watchCollection('allTariffs', function (newValue) {
      getFilters();
    });

    $scope.$watch('filters.customerType', function (newValue, oldValue) {
      if (newValue && newValue !== oldValue) {
        $scope.getCustomersData();
      }
    });
  });
