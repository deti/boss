import './CronTriggerModel';

describe('CronTriggerModel', function () {
  var CronTriggerModel,
    model = {};

  beforeEach(angular.mock.module('boss.openstackService.CronTriggerModel'));

  beforeEach(inject(function (_CronTriggerModel_) {
    CronTriggerModel = _CronTriggerModel_;
    model = {};
  }));

  it('should parse workflow input json string', function () {
    model.workflow_input = '{"foo": "bar"}';
    model = CronTriggerModel(model);
    expect(model.workflow_input).toEqual({foo: 'bar'});
  });

  it('should ignore invalid json in workflow input', function () {
    model.workflow_input = '{"foo": bar"}';
    model = CronTriggerModel(model);
    expect(model.workflow_input).toEqual('{"foo": bar"}');
  });

  it('should transform next_execution_time to js Date', function () {
    model.next_execution_time = '2015-11-11 11:43:05';
    model = CronTriggerModel(model);
    expect(model.next_execution_time instanceof Date).toBe(true);
  });

  it('should get server instance id from model name', function () {
    model.name = 'backup.server-id';
    model = CronTriggerModel(model);
    expect(model.instanceId).toEqual('server-id');
  });

  it('should add method get display name', function () {
    model.name = 'backup.server-id';
    model = CronTriggerModel(model);
    expect(model.getDisplayName()).toEqual('Backup server-id');
    model.server = {
      name: 'server-name'
    };
    expect(model.getDisplayName()).toEqual('Backup server-name');
  });
});
