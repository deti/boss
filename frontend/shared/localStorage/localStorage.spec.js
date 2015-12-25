import './localStorage';

describe('localStorage', function () {
  var localStorage;
  beforeEach(angular.mock.module('boss.localStorage'));

  beforeEach(inject(function (_localStorage_) {
    localStorage = _localStorage_;
    window.localStorage.clear();
  }));

  it('Should pass dummy test', function () {
    expect(localStorage).toBeTruthy();
  });

  it('Should return default value for empty keys and store it in localStorage', function () {
    var value = localStorage.getItem('some', 'default');
    expect(value).toEqual('default');
    value = localStorage.getItem('some');
    expect(value).toEqual('default');
  });

  it('Should return json-parsed value for object keys', function () {
    localStorage.setItem('key', {key: 'value'});
    var value = localStorage.getItem('key');
    expect(value).toEqual({key: 'value'});
  });

  it('should ignore undefined default value', function () {
    var value = localStorage.getItem('some', undefined);
    expect(value).toBeUndefined();
    value = localStorage.getItem('some');
    expect(value).toBeUndefined();
  });
});
