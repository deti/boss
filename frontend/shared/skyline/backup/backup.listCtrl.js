const dependencies = [
  'restangular',
  'toaster',
  require('../../pollService/pollService').default.name
];

export default angular.module('skyline.backup.listCtrl', dependencies)
  .value('backupActionsTpl', require('./backup.cell.actions.partial.tpl.html'))
  .value('snapshotActionsTpl', require('./snapshot.cell.actions.partial.tpl.html'))
  .controller('OSBackupListCtrl', function OSBackupListCtrl($scope, $filter, snapshots, toaster, Cinder, pollService, backups, Restangular, backupActionsTpl, snapshotActionsTpl) {
    $scope.backupActionsTemplatePath = backupActionsTpl;
    $scope.snapshotActionsTemplatePath = snapshotActionsTpl;
    $scope.snapshots = snapshots;
    snapshots.forEach(snapshot => {
      snapshot.displayName = snapshot.getDisplayName();
    });

    _.filter(snapshots, item => item.status.progress)
      .forEach(pollSnapshot);

    $scope.columns = [
      {
        field: 'displayName',
        title: $filter('translate')('Name')
      },
      {
        title: $filter('translate')('Created'),
        field: 'createdAt',
        width: 180,
        filter: {name: 'date', args: ['short']}
      },
      {
        title: $filter('translate')('Size'),
        field: 'size',
        width: 165,
        filter: {name: 'bytes', args: ['GB']}
      },
      {
        field: 'status.title',
        title: $filter('translate')('Status'),
        width: 180,
        filter: 'translate',
        template: '{{item.status.title | translate}}<span ng-if="item.status.progress">...</span>'
      }
    ];

    $scope.removeSnapshot = function (snapshot) {
      snapshot.remove()
        .then(() => {
          pollSnapshot(snapshot);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    function pollSnapshot(snapshot) {
      var promise = pollService
        .asyncTask(() => {
          return Cinder.snapshot(snapshot.id);
        }, serverRsp => {
          if (serverRsp.status.value !== snapshot.status) {
            Restangular.sync(serverRsp, snapshot);
            snapshot.status = serverRsp.status;
          }
          return !serverRsp.status.progress;
        });
      promise
        .then(serverRsp => {
          Restangular.sync(serverRsp, snapshot);
          snapshot.status = serverRsp.status;
        })
        .catch(e => {
          if (e.status === 404) {
            _.remove(snapshots, snapshot);
          }
        });
      $scope.$on('$destroy', promise.stop);
    }

    $scope.backups = backups;
    backups.forEach(backup => {
      backup.displayName = backup.getDisplayName();
    });
    $scope.backupsColumns = [
      {
        title: $filter('translate')('Name'),
        field: 'displayName'
      },
      {
        title: $filter('translate')('Execution time'),
        field: 'pattern',
        filter: 'cronToText'
      },
      {
        title: $filter('translate')('Next schedule'),
        field: 'next_execution_time',
        filter: {name: 'date', args: ['short']}
      }
    ];

    $scope.removeBackup = function (backup) {
      backup.remove()
        .then(function () {
          toaster.pop('success', $filter('translate')('Removed from schedule'));
          var index = _.findIndex($scope.backups, backup);
          backups.splice(index, 1);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };
  });
