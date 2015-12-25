const dependencies = [
  'toaster',
  require('../../../lib/serviceService/serviceService').default.name
];

export default angular.module('boss.admin.services.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('services.new', {
        url: '/new/',
        views: {
          'details@boss': {
            template: require('./services.new.tpl.html'),
            controller: 'ServicesNewCtrl'
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'New service'
        },
        resolve: {
          measures: function (serviceService) {
            return serviceService.measures({measure_type: 'time'});
          }
        }
      });
  })
  .controller('ServicesNewCtrl', function ($scope, serviceService, toaster, $filter, measures, $state) {
    $scope.service = {};
    $scope.measures = measures;
    $scope.create = function (form) {
      serviceService.createCustom($scope.service.localized_name, $scope.service.description, $scope.service.measure)
        .then(function () {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Service is created'));
          $state.go('services', {}, {reload: true});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
    $scope.cancel = function () {
      $state.go('services');
    };
  });
