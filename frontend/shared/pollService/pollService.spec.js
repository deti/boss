import './pollService';

describe('pollService', function () {
  var pollService, $timeout, $q;
  beforeEach(angular.mock.module('boss.pollService'));

  beforeEach(inject(function (_pollService_, _$timeout_, _$q_) {
    pollService = _pollService_;
    $timeout = _$timeout_;
    $q = _$q_;
  }));


  var numCalled = 0;

  function task() {
    numCalled++;
    return $q.when({foo: `bar-${numCalled}`});
  }

  beforeEach(function () {
    numCalled = 0;
  });

  it('should poll new data', function () {
    var obj = {
      foo: 'foo'
    };
    var id = pollService.startPolling(task, obj, 100);
    $timeout.flush(100);
    expect(obj.foo).toBe('bar-1');
    pollService.stopPolling(id);
    $timeout.flush(100);
    expect(obj.foo).toBe('bar-1');
  });

  it('should stop polling when limit reached', function () {
    var promise = pollService.startPolling(task, {}, 10, 2);
    var catcher = {
      fn: function () {
      }
    };
    spyOn(catcher, 'fn');
    promise.catch(catcher.fn);
    $timeout.flush(10);
    $timeout.flush(10);
    $timeout.flush(10);
    expect(catcher.fn).toHaveBeenCalled();
  });

  it('should perform requests until stop function return true', function () {
    var promise = pollService.asyncTask(task, function (rsp) {
      return rsp.foo === 'bar-1';
    });
    var catcher = {
      fn: function () {
      }
    };
    spyOn(catcher, 'fn');
    promise.then(catcher.fn);

    $timeout.flush(pollService.sigmoidTiming(1));
    expect(catcher.fn).toHaveBeenCalled();
  });
});
