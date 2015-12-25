import './bytesFilter';

describe('bytesFilter', function () {
  var bytesFilter;
  beforeEach(angular.mock.module('boss.bytesFilter'));
  beforeEach(inject(function ($filter) {
    bytesFilter = $filter('bytes');
  }));

  it('should return "-" if no number was passed', function () {
    var val = bytesFilter('hello');

    expect(val).toBe('-');
  });

  it('should convert bytes to kb', function () {
    var val = bytesFilter(2048);

    expect(val).toBe('2 kB');
  });

  it('should convert bytes to kb with precision', function () {
    var val = bytesFilter(2500, 'bytes', 1);

    expect(val).toBe('2.4 kB');
  });

  it('should convert kb to mb', function () {
    var val = bytesFilter(2048, 'kB');

    expect(val).toBe('2 MB');
  });

  it('should accept baseUnit in any case', function () {
    var val = bytesFilter(2048, 'Kb');

    expect(val).toBe('2 MB');
  });

  it('should set base unit to bytes if pass incorrect unit', function () {
    var val = bytesFilter(2048, 'miles');

    expect(val).toBe('2 kB');
  });

  it('should correct handle zero', function () {
    var val = bytesFilter(0);

    expect(val).toBe('0 bytes');

    val = bytesFilter(0, 'gb');
    expect(val).toBe('0 GB');
  });
});
