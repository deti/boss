const dependencies = [
  require('./BaseOpenstack').default.name,
  require('./CronTriggerModel').default.name,
  require('./Nova').default.name
];

export default angular.module('boss.openstackService.Mistral', dependencies)
  .factory('Mistral', function (BaseOpenstack, CronTriggerModel, $q, Nova) {
    class Mistral extends BaseOpenstack {
      constructor() {
        super('/mistral/v2/');
        this.Restangular.extendModel('cron_triggers', CronTriggerModel);
        this.Restangular.setRestangularFields({
          id: 'name'
        });
      }

      cronTriggers() {
        return this.Restangular.all('cron_triggers').getList();
      }

      createCronTrigger(trigger) {
        return this.Restangular.all('cron_triggers').post(trigger);
      }

      backups() {
        return this.cronTriggers()
          .then(list => {
            return _.filter(list, item => item.workflow_name === 'make_backup');
          });
      }

      backupsWithLinkedServers() {
        return this.backups()
          .then(backups => {
            var promises = backups.map(b => this.backupLinkedServer(b));
            return $q.all(promises);
          });
      }

      backupLinkedServer(backup) {
        return Nova.server(backup.instanceId)
          .then(server => {
            backup.server = server;
            return backup;
          })
          .catch(e => {
            backup.server = false;
            return backup;
          });
      }

      backupsForServer(serverId) {
        return this.backups()
          .then(list => {
            return _.filter(list, item => item.workflow_input && item.workflow_input.server_id === serverId);
          });
      }

      createBackup(serverId, hours, minutes = 0, dayOfWeek = '*', keepLastN = 3) {
        var req = {
          name: `backup.${serverId}.${Date.now()}`,
          pattern: `${minutes} ${hours} * * ${dayOfWeek}`,
          workflow_name: 'make_backup',
          workflow_input: JSON.stringify({
            server_id: serverId,
            prefix: `backup.${serverId}.`,
            keep_last_n: keepLastN
          })
        };
        return this.createCronTrigger(req);
      }
    }

    return new Mistral();
  });
