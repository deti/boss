const dependencies = ['toaster'];

export default angular.module('skyline.servers.editBackupsCtrl', dependencies)
  .value('serverBackupActionsTpl', require('./cell.actions.backups.partial.tpl.html'))
  .controller('OSServersEditBackupsCtrl', function OSServersEditBackupsCtrl($scope, $filter, backups, Mistral, server, toaster, serverBackupActionsTpl) {
    $scope.actionsTplPath = serverBackupActionsTpl;
    $scope.backups = backups;
    $scope.backup = {
      time: new Date(1970, 0, 1, 12, 0, 0),
      week: '*',
      keep_last_n: 2
    };
    $scope.createBackup = function (form) {
      if (form.$invalid) {
        return;
      }
      Mistral.createBackup(server.id, $scope.backup.time.getHours(), $scope.backup.time.getMinutes(), $scope.backup.week, $scope.backup.keep_last_n)
        .then(backup => {
          backups.push(backup);
        })
        .catch(e => {
          if (e.status === 409) {
            e.data.faultstring = $filter('translate')('Backup on this time has been already planned');
          }
          toaster.pop('error', e.data.faultstring || $filter('translate')('Error on backup planning'));
        });
    };

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

    $scope.backupsColumns = [
      {
        title: $filter('translate')('Repeating'),
        field: 'pattern',
        filter: 'cronToText'
      },
      {
        field: 'execTimeString',
        title: $filter('translate')('Execution time')
      },
      {
        field: 'next_execution_time',
        title: $filter('translate')('Next schedule'),
        filter: {name: 'date', args: ['short']}
      }
    ];
  });
