const dependencies = [
  'restangular',
  'toaster',
  require('../../openstackService/Glance').default.name,
  require('../../pollService/pollService').default.name,
  require('../../bytesFilter/bytesFilter').default.name
];

export default angular.module('skyline.images.listCtrl', dependencies)
  .value('imgActionTpl', require('./cell.actions.partial.tpl.html'))
  .controller('OSImagesCtrl', function OSImagesCtrl($scope, images, $filter, toaster, IMAGE_STATUS, Glance, pollService, Restangular, imgActionTpl) {
    $scope.IMAGE_STATUS = IMAGE_STATUS;
    images = _.filter(images, {disk_format: 'iso'});
    $scope.images = images;
    $scope.actionsTemplatePath = imgActionTpl;

    _.filter(images, item => item.status.progress)
      .forEach(pollImage);

    $scope.removeImage = function (image) {
      image.remove()
        .then(function () {
          toaster.pop('success', $filter('translate')('Image was successfully deleted'));
          var index = _.findIndex($scope.images, image);
          images.splice(index, 1);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.columns = [
      {
        field: 'name',
        title: $filter('translate')('Name')
      },
      {
        field: 'own',
        title: $filter('translate')('Type'),
        value: function (item) {
          return item.own ? $filter('translate')('User') : $filter('translate')('Pre-installed');
        }
      },
      {
        field: 'size',
        title: $filter('translate')('Size'),
        value: function (item) {
          if (item.status.progress) {
            return item.status.title;
          }
          if (item.size) {
            return $filter('bytes')(item.size);
          } else {
            return '-';
          }
        }
      }
    ];

    function pollImage(image) {
      var promise = pollService
        .asyncTask(() => {
          return Glance.image(image.id);
        }, serverRsp => {
          if (serverRsp.status.value !== image.status) {
            Restangular.sync(serverRsp, image);
            image.status = serverRsp.status;
          }
          return !serverRsp.status.progress;
        });
      promise
        .then(serverRsp => {
          Restangular.sync(serverRsp, image);
          image.status = serverRsp.status;
        })
        .catch(e => {
          if (e.status === 404) {
            _.remove(images, image);
          }
        });
      $scope.$on('$destroy', promise.stop);
    }
  });
