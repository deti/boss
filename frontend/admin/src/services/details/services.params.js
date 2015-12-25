const dependencies = [
  require('../../../lib/serviceService/serviceService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];

export default angular.module('boss.admin.services.params', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('services.details.params', {
        url: '/params',
        views: {
          'detail': {
            template: require('./services.params.tpl.html'),
            controller: 'ServicesDetailsParamsCtrl'
          }
        }
      });
  })
  .controller('ServicesDetailsParamsCtrl', function ($scope, $state, service, Restangular, serviceService, $filter, toaster, measures, popupErrorService) {
    $scope.service = Restangular.copy(service);

    if ($scope.service.mutable) {
      $scope.measures = _.where(measures, {measure_type: 'time'});
    } else {
      $scope.measures = measures;
    }

    $scope.isCustom = function (service) {
      return service.category.category_id === 'custom';
    };

    $scope.save = function (form) {
      serviceService.editCustom($scope.service)
        .then(function () {
          toaster.pop('success', $filter('translate')('Service is successfully changed'));
          $state.go($state.current.name, {}, {reload: true});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.remove = function () {
      serviceService.remove($scope.service)
        .then(function () {
          toaster.pop('success', $filter('translate')('Service is successfully deleted'));
          $state.go('services', {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.activate = function () {
      serviceService.makeImmutable($scope.service.service_id)
        .then(function () {
          toaster.pop('success', $filter('translate')('Service is successfully changed'));
          $state.go($state.current.name, {}, {reload: true});
        }, function (err) {
          popupErrorService.show(err);
        });
    };
  });
