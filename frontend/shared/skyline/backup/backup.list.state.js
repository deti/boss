const dependencies = [
  require('./backup.listCtrl').default.name
];

export default angular.module('skyline.backup.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.backup', {
        url: 'backup',
        abstract: true
      })
      .state('openstack.backup.list', {
        url: '/',
        views: {
          'main@boss': {
            controller: 'OSBackupListCtrl',
            template: require('./backup.list.tpl.html')
          }
        },
        data: {
          pageTitle: 'Backup'
        },
        resolve: {
          snapshots: function (osServices) {
            return osServices.Cinder.snapshotsWithLinkedServers();
          },
          backups: function (osServices) {
            return osServices.Mistral.backupsWithLinkedServers();
          }
        }
      });
  });
