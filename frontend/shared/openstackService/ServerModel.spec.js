import './ServerModel';

describe('ServerModel', function () {
  var ServerModel,
    SERVER_STATUS,
    model = {};

  beforeEach(angular.mock.module('boss.openstackService.ServerModel'));

  beforeEach(inject(function (_ServerModel_, _SERVER_STATUS_) {
    ServerModel = _ServerModel_;
    SERVER_STATUS = _SERVER_STATUS_;
    model = {
      post: function () {
      }
    };
    spyOn(model, 'post').and.returnValue({
      then: function () {
      }
    });
  }));

  it('should set model status', function () {
    model.status = SERVER_STATUS.ACTIVE.value;
    model = ServerModel(model);
    expect(model.status).toEqual(SERVER_STATUS.ACTIVE);
  });

  it('should set model status to progress if OS-EXT-STS:task_state is defined', function () {
    model.status = SERVER_STATUS.ACTIVE.value;
    model['OS-EXT-STS:task_state'] = 'rebuild';
    model = ServerModel(model);
    expect(model.status.progress).toEqual(true);
  });

  it('should transform model.addresses to array', function () {
    model.addresses = {
      DefaultPrivateNet: [
        {ip: '1.2.3.4'}
      ],
      OtherNet: [
        {ip: '4.3.2.1'},
        {ip: '5.6.7.8'}
      ]
    };
    model = ServerModel(model);

    expect(model.ips).toEqual([{ip: '1.2.3.4'}, {ip: '4.3.2.1'}, {ip: '5.6.7.8'}])
  });
});
