const dependencies = [
  'toaster',
  require('../../../shared/dialog/dialog').default.name
];

export default angular.module('skyline.simple.RecreateCtrl', dependencies)
  .controller('RecreateCtrl', function RecreateCtrl($scope, $filter, $state, toaster, osServices, server, images, dialog) {
    $scope.images = _.filter(images, item => item.disk_format != 'iso');
    $scope.serverParams = {
      name: server.name,
      imageRef: server.image.id || $scope.images[0].id
    };

    $scope.recreate = function (form) {
      if (form.$invalid) {
        return;
      }
      dialog.confirm(
        $filter('translate')('Dear customer, during recreation process all your data will be lost. Are you sure?'),
        $filter('translate')('Yes'),
        $filter('translate')('Cancel')
      ).then(() => {
        $scope.formDisabled = true;

        server.rebuild($scope.serverParams)
          .then(function () {
            toaster.pop('success', $filter('translate')('Server was successfully recreated'));
            $state.go('openstack.simple', {}, {reload: true, inherit: false});
          })
          .catch(e => {
            Raven.captureException(JSON.stringify(e));
            toaster.pop('error', $filter('translate')('Error in recreate process'));
            $scope.formDisabled = false;
          });
      });
    };
  });
