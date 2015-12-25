const dependencies = ['pascalprecht.translate'];

export default angular.module('boss.openstackService.SnapshotModel', dependencies)
  .factory('SnapshotModel', function (SNAPSHOT_STATUS, $filter) {
    function extendSnapshotModel(model) {
      if (_.startsWith(model.name, 'backup')) {
        model.instanceId = model.name.split('.')[1];
      }
      if (model.status && typeof model.status === 'string') {
        if (typeof SNAPSHOT_STATUS[model.status] !== 'undefined') {
          model.status = angular.copy(SNAPSHOT_STATUS[model.status]);
        } else {
          console.log('unknown snapshot status', model.status);
        }
      }
      if (model.created_at) {
        model.createdAt = new Date(model.created_at + '+00:00');
      }
      model.getDisplayName = function () {
        if (model.instanceId) {
          return $filter('translate')('Backup') + ' ' + (model.server ? model.server.name : model.instanceId);
        }
        return model.name;
      };

      return model;
    }

    return extendSnapshotModel;
  })
  .factory('SNAPSHOT_STATUS', function ($filter) {
    return {
      creating: {title: $filter('translate')('Creating'), value: 'creating', progress: true},
      available: {title: $filter('translate')('Available'), value: 'available'},
      deleting: {title: $filter('translate')('Process of removal'), value: 'deleting', progress: true},
      error: {title: $filter('translate')('Error'), value: 'error'},
      error_deleting: {title: $filter('translate')('Error in the removal process'), value: 'error_deleting'}
    };
  });
