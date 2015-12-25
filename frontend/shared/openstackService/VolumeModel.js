const dependencies = ['pascalprecht.translate'];

export default angular.module('boss.openstackService.VolumeModel', dependencies)
  .factory('VolumeModel', function (VOLUME_STATUS) {
    function extendVolumeModel(model) {
      model.extend = function (newSize) {
        return model
          .post('action', {
            'os-extend': {
              new_size: newSize
            }
          });
      };

      model.createImage = function (imageName) {
        return model
          .post('action', {
            'os-volume_upload_image': {
              'image_name': imageName
            }
          });
      };

      if (model.status && typeof model.status === 'string') {
        if (typeof VOLUME_STATUS[model.status] !== 'undefined') {
          model.status = angular.copy(VOLUME_STATUS[model.status]);
        } else {
          console.log('unknown volume status', model.status);
        }
      }
      return model;
    }

    return extendVolumeModel;
  })
  .factory('VOLUME_STATUS', function ($filter) { // don't use constant because we need translate here
    return {
      // static states
      'available': {title: $filter('translate')('Available'), value: 'available'},
      'in-use': {title: $filter('translate')('In use'), value: 'in-use'},
      'error': {title: $filter('translate')('Error'), value: 'error'},
      'error_deleting': {title: $filter('translate')('Error in the removal process'), value: 'error_deleting'},
      'error_restoring': {title: $filter('translate')('Backup error'), value: 'error_restoring'},
      'error_extending': {title: $filter('translate')('Extension error'), value: 'error_extending'},

      // progress
      'creating': {title: $filter('translate')('Creating'), value: 'creating', progress: true},
      'deleting': {title: $filter('translate')('Removal'), value: 'deleting', progress: true},
      'attaching': {title: $filter('translate')('Attachment in the process'), value: 'attaching', progress: true},
      'detaching': {title: $filter('translate')('Removing'), value: 'detaching', progress: true},
      'uploading': {title: $filter('translate')('Uploading'), value: 'uploading', progress: true},
      'downloading': {title: $filter('translate')('Uploading'), value: 'downloading', progress: true},
      'backing-up': {title: $filter('translate')('Backup creation'), value: 'backing-up', progress: true},
      'restoring-backup': {
        title: $filter('translate')('Restore backup'),
        value: 'restoring-backup',
        progress: true
      }
    };
  });
