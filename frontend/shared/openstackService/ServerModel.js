const dependencies = ['pascalprecht.translate'];

export default angular.module('boss.openstackService.ServerModel', dependencies)
  .factory('ServerModel', function (SERVER_STATUS) {
    function serverModelExtend(model) {
      model.stop = function () {
        return model
          .post('action', {
            'os-stop': null
          })
          .then(function () {
            model.status.progress = true;
          });
      };
      model.start = function () {
        return model
          .post('action', {
            'os-start': null
          })
          .then(function () {
            model.status.progress = true;
          });
      };
      model.reboot = function () {
        return model
          .post('action', {
            reboot: {
              type: 'SOFT'
            }
          })
          .then(function () {
            model.status.progress = true;
          });
      };
      model.resize = function (flavorRef) {
        return model.post('action', {
          resize: {
            flavorRef
          }
        });
      };

      model.confirmResize = function () {
        return model.post('action', {
          confirmResize: null
        });
      };

      model.pause = function () {
        return model
          .post('action', {
            pause: null
          })
          .then(function () {
            model.status.progress = true;
          });
      };

      model.unpause = function () {
        return model
          .post('action', {
            unpause: null
          })
          .then(function () {
            model.status.progress = true;
          });
      };

      model.suspend = function () {
        return model
          .post('action', {
            suspend: null
          })
          .then(function () {
            model.status.progress = true;
          });
      };

      model.resume = function () {
        return model
          .post('action', {
            resume: null
          })
          .then(function () {
            model.status.progress = true;
          });
      };

      model.createImage = function (name) {
        return model
          .post('action', {
            createImage: {
              name
            }
          });
      };

      model.addIp = function (address) {
        return model
          .post('action', {
            addFloatingIp: {
              address
            }
          });
      };

      model.vncConsole = function () {
        return model
          .post('action', {
            'os-getVNCConsole': {
              type: 'novnc'
            }
          });
      };

      model.rescueMode = function (imageId) {
        return model
          .post('action', {
            rescue: {
              rescue_image_ref: imageId
            }
          });
      };

      model.unrescue = function () {
        return model
          .post('action', {
            unrescue: null
          });
      };

      model.rebuild = function (serverParams) {
        return model
          .post('action', {
            rebuild: serverParams
          });
      };

      if (model.status && typeof model.status === 'string') {
        if (typeof SERVER_STATUS[model.status] !== 'undefined') {
          model.status = angular.copy(SERVER_STATUS[model.status]);
          if (model['OS-EXT-STS:task_state'] === 'deleting') {
            model.status = angular.copy(SERVER_STATUS.DELETING);
          }
          if (model['OS-EXT-STS:task_state']) {
            model.status.progress = true;
          }
        } else {
          console.log('unknown server status', model.status);
        }
      }

      model.ips = [];
      if (model.addresses) {
        Object.keys(model.addresses).forEach(key => {
          model.ips = model.ips.concat(model.addresses[key]);
        });
      }

      return model;
    }

    return serverModelExtend;
  })
  .factory('SERVER_STATUS', function ($filter) { // don't use constant because we need translate here
    return {
      // static states
      ACTIVE: {title: $filter('translate')('Running'), value: 'ACTIVE'},
      SHUTOFF: {title: $filter('translate')('Stopped'), value: 'SHUTOFF'},
      PAUSED: {title: $filter('translate')('Paused'), value: 'PAUSED'},
      SUSPENDED: {title: $filter('translate')('Paused'), value: 'SUSPENDED'},

      // need action
      VERIFY_RESIZE: {title: $filter('translate')('Re-size confirmal'), value: 'VERIFY_RESIZE'},
      ERROR: {title: $filter('translate')('Error'), value: 'ERROR'},
      DELETED: {title: $filter('translate')('Removed'), value: 'DELETED'},
      RESCUE: {title: $filter('translate')('Restoration'), value: 'RESCUE'},

      // progress
      BUILD: {title: $filter('translate')('Creating'), value: 'BUILD', progress: true},
      REBUILD: {title: $filter('translate')('Recreating'), value: 'REBUILD', progress: true},
      RESIZE: {title: $filter('translate')('Re-size'), value: 'RESIZE', progress: true},
      MIGRATING: {title: $filter('translate')('Moving'), value: 'MIGRATING', progress: true},
      REBOOT: {title: $filter('translate')('Reboot'), value: 'REBOOT', progress: true},

      // own progress states
      DELETING: {title: $filter('translate')('Process of removal'), value: 'DELETING', progress: true}
    };
  });
