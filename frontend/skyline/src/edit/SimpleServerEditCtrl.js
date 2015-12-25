const dependencies = [
  'toaster',
  require('../../../shared/skyline/servers/server.editCtrl').default.name,
  require('../../../shared/openstackService/ServerModel').default.name,
  require('../../../shared/pollService/pollService').default.name
];

export default angular.module('skyline.simple.SimpleServerEditCtrl', dependencies)
  .controller('SimpleServerEditCtrl', function SimpleServerEditCtrl($scope, $controller, osServices, server, images, $filter, toaster, SERVER_STATUS, pollService) {
    angular.extend(this, $controller('OSServersEditCtrl', {
      $scope,
      osServices,
      server,
      availableVolumes: [],
      volumes: [],
      flavors: [],
      ips: []
    }));

    $scope.SERVER_STATUS = SERVER_STATUS;
    $scope.images = _.filter(images, {disk_format: 'iso'});
    $scope.rescue = {
      rescueImage: null
    };
    $scope.setRescueMode = function (form) {
      console.log($scope.rescue.rescueImage);
      server.rescueMode($scope.rescue.rescueImage)
        .then(() => {
          return pollService
            .asyncTask(function () {
              return osServices.Nova.server(server.id);
            }, serverPollingStopFn);
        })
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Server now in the rescue mode'));
          server.status = rsp.status;
          form.$resetSubmittingState();
        })
        .catch(e => {
          toaster.pop('error', 'Error while moving to rescue mode');
          form.$parseErrors(e);
        });
    };
    $scope.rescueSubmitting = false;
    $scope.setUnrescueMode = function () {
      $scope.rescueSubmitting = true;
      server.unrescue()
        .then(() => {
          return pollService
            .asyncTask(function () {
              return osServices.Nova.server(server.id);
            }, serverPollingStopFn);
        })
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Exit from rescue mode'));
          $scope.rescueSubmitting = false;
          server.status = rsp.status;
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error on exit from rescue mode'));
          $scope.rescueSubmitting = false;
        });
    };

    function serverPollingStopFn(rsp) {
      return rsp.status.value !== server.status.value;
    }
  });
