const dependencies = [
  'restangular',
  require('../../../lib/customerService/customerService').default.name,
  require('../../../lib/utilityService/utilityService').default.name
];

const editEntityTplPath = require('./customer.edit.entity.partial.tpl.html');
const editPrivateTplPath = require('./customer.edit.private.partial.tpl.html');

export default angular.module('boss.admin.customer.info', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.info', {
        url: '/info',
        views: {
          'detail': {
            template: require('./customer.info.tpl.html'),
            controller: 'MainDetailsInfoCtrl'
          }
        },
        resolve: {
          customerLocales: function (utilityService) {
            return utilityService.customerLocales();
          },
          periodOption: function (utilityService) {
            return utilityService.withdrawPeriod('auto_report');
          },
          countries: function (utilityService, locale) { // locale need to be loaded before list of countries
            return utilityService.countries();
          }
        }
      });
  })
  .controller('MainDetailsInfoCtrl', function ($scope, $filter, customer, countries, customerService, toaster, Restangular, customerLocales, periodOption) {
    $scope.editEntityTplPath = editEntityTplPath;
    $scope.editPrivateTplPath = editPrivateTplPath;
    $scope.countries = countries;
    $scope.periodOption = periodOption;
    $scope.customerLocales = customerLocales;
    $scope.customer = Restangular.copy(customer);

    $scope.osDashboards = [
      {value: 'horizon', title: $filter('translate')('Horizon')},
      {value: 'skyline', title: $filter('translate')('Simple')},
      {value: 'both', title: $filter('translate')('Both')}
    ];

    $scope.selectLocale = function (localeCode) {
      return $scope.customer.locale.toUpperCase() === localeCode.toUpperCase();
    };

    $scope.update = function (form) {
      customerService.update($scope.customer)
        .then(function (rsp) {
          Restangular.sync(rsp.customer_info, $scope.customer);
          Restangular.sync(rsp.customer_info, customer);
          toaster.pop('success', $filter('translate')('User account is successfully changed'));
        }).catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
