import './VolumeModel';

describe('VolumeModel', function () {
  var VolumeModel,
    VOLUME_STATUS,
    model = {};

  beforeEach(angular.mock.module('boss.openstackService.VolumeModel'));

  beforeEach(inject(function (_VolumeModel_, _VOLUME_STATUS_) {
    VOLUME_STATUS = _VOLUME_STATUS_;
    VolumeModel = _VolumeModel_;
    model = {
      post: function () {
      }
    };
    spyOn(model, 'post');
  }));

  it('should set model status', function () {
    model.status = VOLUME_STATUS.attaching.value;
    model = VolumeModel(model);
    expect(model.status).toEqual(VOLUME_STATUS.attaching);
  });

  it('should ignore unknown statuses', function () {
    model.status = 'foo';
    model = VolumeModel(model);
    expect(model.status).toEqual('foo');
  });

  it('should add extend method to model', function () {
    model = VolumeModel(model);
    model.extend(5);

    expect(model.post).toHaveBeenCalledWith('action', {'os-extend': {new_size: 5}});
  });
});
