const dependencies = ['toaster'];

export default angular.module('skyline.images.newCtrl', dependencies)
  .controller('OSImagesNewCtrl', function OSImagesNewCtrl($scope, $filter, $state, Glance, toaster) {
    $scope.image = {};

    $scope.downloadImage = function (form) {
      Glance.createImage($scope.image)
        .then(function (rsp) {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('The image was successfully uploaded'));
          $state.go('openstack.images', {}, {reload: true});
        })
        .catch(function (err) {
          form.$resetSubmittingState();
          toaster.pop('error', $filter('translate')('Failed to upload the image'));
        });
    };
  });
