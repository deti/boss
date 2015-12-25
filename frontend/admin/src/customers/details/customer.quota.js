const dependencies = [
  'toaster',
  require('../../../lib/customerService/customerService').default.name,
  require('../../../lib/utilityService/utilityService').default.name
];

export default angular.module('boss.admin.customer.quota', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('main.details.quota', {
        url: '/quota',
        views: {
          'detail': {
            template: require('./customer.quota.tpl.html'),
            controller: 'MainDetailsQuotaCtrl'
          }
        },
        resolve: {
          quotas: function (customerService, customer) {
            return customerService.quotas(customer);
          },
          templates: function (utilityService) {
            return utilityService.quotasTemplates();
          }
        }
      });
  })
  .controller('MainDetailsQuotaCtrl', function ($scope, $filter, quotas, customerService, templates, customer, toaster) {
    $scope.templates = templates;
    $scope.selected_template = 'new';
    $scope.quotas = quotas;
    $scope.updateQuotas = function (form) {
      var promise;
      if ($scope.selected_template === 'new') {
        promise = customerService.updateQuotas(customer, $scope.quotas);
      } else {
        promise = customerService.applyQuotaTemplate(customer, $scope.selected_template);
      }
      promise
        .then(function () {
          toaster.pop('success', $filter('translate')('Quotas are updated'));
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    var templateChanged = false;
    $scope.$watch('selected_template', value => {
      if (value === 'new') {
        return;
      }
      templateChanged = true;
      $scope.quotas = angular.copy(_.find(templates, {template_id: value}).template_info);
    });

    $scope.$watch('quotas', value => {
      if (templateChanged) {
        templateChanged = false;
        return;
      }
      $scope.selected_template = 'new';
    }, true);
  });
