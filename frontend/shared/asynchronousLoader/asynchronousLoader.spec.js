import './asynchronousLoader';

describe('asynchronousLoader', function () {
  var asynchronousLoader;
  beforeEach(angular.mock.module('boss.asynchronousLoader'));

  beforeEach(inject(function (_asynchronousLoader_) {
    asynchronousLoader = _asynchronousLoader_;
  }));

  it('should pass dummy test', function () {
    expect(asynchronousLoader).toBeTruthy();
  });

  it('should add script tag to body', function () {
    asynchronousLoader.load('test.js');

    expect($('script[src*="test.js"]').length).toBe(1);
  });

  it('Shouldn\'t add one script more than once', function () {
    asynchronousLoader.load('test.js');
    asynchronousLoader.load('test.js');
    asynchronousLoader.load('test.js');

    expect($('script[src*="test.js"]').length).toBe(1);
  });
});
