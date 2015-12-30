const dependencies = [
  'pascalprecht.translate',
  require('../leadingZerosFilter/leadingZerosFilter').default.name
];
import moment from 'moment';

export default angular.module('boss.openstackService.CronTriggerModel', dependencies)
  .factory('CronTriggerModel', function ($filter) {
    function extendCronTrigger(model) {
      if (model.workflow_input && typeof model.workflow_input === 'string') {
        try {
          model.workflow_input = JSON.parse(model.workflow_input);
        } catch (e) {
          console.log('Unable to parse workflow input');
        }
      }
      if (model.next_execution_time) {
        model.next_execution_time = moment(model.next_execution_time).toDate();
      }
      if (model.pattern) {
        model.execTime = parseCronPattern(model.pattern);
        model.execTimeString = $filter('leadingZeros')(model.execTime.hours) + ':' + $filter('leadingZeros')(model.execTime.minutes);
      }
      if (_.startsWith(model.name, 'backup.')) {
        model.instanceId = model.name.split('.')[1];
      }

      model.getDisplayName = function () {
        return $filter('translate')('Backup') + ' ' + (model.server ? model.server.name : model.instanceId);
      };

      return model;
    }

    function parseCronPattern(pattern) {
      var blocks = pattern.split(' ');
      return {
        month: blocks[3] || '*',
        day: blocks[2] || '*',
        hours: blocks[1] || '*',
        minutes: blocks[0] || '*',
        dayOfWeek: blocks[4] || '*'
      };
    }

    return extendCronTrigger;
  });
