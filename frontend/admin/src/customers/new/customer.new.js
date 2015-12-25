const dependencies = [
  require('../../../lib/customerService/customerService').default.name,
  require('../../../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.admin.customer.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.new', {
        url: '/new',
        views: {
          'details@boss': {
            template: require('./customer.new.tpl.html'),
            controller: 'MainNewCtrl'
          },
          'tab-info@main.new': {
            template: require('./customer.new.1.tpl.html')
          },
          'private@main.new': {
            template: require('./customer.new.1.private.tpl.html')
          },
          'entity@main.new': {
            template: require('./customer.new.1.entity.tpl.html')
          },
          'tab-contacts@main.new': {
            template: require('./customer.new.2.tpl.html')
          },
          'private-contacts@main.new': {
            template: require('./customer.new.2.private.tpl.html')
          },
          'entity-contacts@main.new': {
            template: require('./customer.new.2.entity.tpl.html')
          }
        },
        resolve: {
          customerLocales: function (utilityService) {
            return utilityService.customerLocales();
          },
          countries: function (utilityService) {
            return utilityService.countries();
          },
          customerMode: function (utilityService) {
            return utilityService.customerMode();
          },
          periodOption: function (utilityService) {
            return utilityService.withdrawPeriod('auto_report');
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'New customer'
        }
      });
  })
  .controller('MainNewCtrl', function ($scope, $state, $filter, toaster, customerService, CONST, customerLocales, countries, periodOption, customerMode) {
    $scope.activeTab = 1;
    $scope.customer = {};
    $scope.customerLocales = customerLocales;
    $scope.countries = countries;
    $scope.periodOption = periodOption;
    $scope.modes = customerMode;
    $scope.forms = {};

    var setDefaults = function () {
      $scope.customer.locale = CONST.defaultLocale.split('-')[0];
      $scope.customer.customer_mode = 'test';
      $scope.customer.withdraw_period = 'week';
    };

    var init = function () {
      $scope.customer.customer_type = 'private';
      setDefaults();
    };

    var resetType = function (type) {
      angular.copy({}, $scope.customer);
      $scope.customer.customer_type = type;
      setDefaults();
    };

    init();

    $scope.$watch('customer.customer_type', function (newValue) {
      resetType(newValue);
    });

    $scope.showTab = function (id) {
      $scope.activeTab = id;
    };

    $scope.isActive = function (id) {
      return $scope.activeTab === id;
    };

    $scope.create = function (form) {
      customerService.createCustomer($scope.customer)
        .then(function (rsp) {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Customer\'s account has been successfully created.'));
          $state.go('main', {}, {reload: true});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.finish = function () {
      $state.go('main');
    };

    $scope.manyTabs = false;
    $scope.tabs = [
      {id: 1, title: $filter('translate')('Step 1 - Information')},
      {id: 2, title: $filter('translate')('Step 2 - Contacts')}
    ];
  });
