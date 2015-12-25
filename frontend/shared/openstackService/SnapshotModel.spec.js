import './SnapshotModel';

describe('SnapshotModel', function () {
  var SnapshotModel,
    SNAPSHOT_STATUS,
    model = {};

  beforeEach(angular.mock.module('boss.openstackService.SnapshotModel'));

  beforeEach(inject(function (_SnapshotModel_, _SNAPSHOT_STATUS_) {
    SNAPSHOT_STATUS = _SNAPSHOT_STATUS_;
    SnapshotModel = _SnapshotModel_;
    model = {};
  }));

  it('should set model status', function () {
    model.status = SNAPSHOT_STATUS.available.value;
    model = SnapshotModel(model);
    expect(model.status).toEqual(SNAPSHOT_STATUS.available);
  });

  it('should ignore unknown statuses', function () {
    model.status = 'foo';
    model = SnapshotModel(model);
    expect(model.status).toEqual('foo');
  });

  it('should extract instanceId from model name', function () {
    model.name = 'backup.server-id.rest_of_the_name';
    model = SnapshotModel(model);

    expect(model.instanceId).toEqual('server-id');
  });

  it('should add method to get display name for model', function () {
    model.name = 'backup.server-id.rest_of_the_name';
    model = SnapshotModel(model);

    expect(model.getDisplayName()).toEqual('Backup server-id');
    model.server = {
      name: 'server-name'
    };
    expect(model.getDisplayName()).toEqual('Backup server-name');

    model.instanceId = false;
    expect(model.getDisplayName()).toEqual('backup.server-id.rest_of_the_name');
  });

  it('should transform created_at to Date', function () {
    model.created_at = '2015-11-11 11:43:05';
    model = SnapshotModel(model);

    expect(model.createdAt instanceof Date).toBe(true);
  });
});
