import './pickFilter';

describe('pickFilter', function () {
  var pickFilter;
  beforeEach(angular.mock.module('boss.pickFilter'));
  beforeEach(inject(function ($filter) {
    pickFilter = $filter('pickFilter');
  }));

  it('should pass a dummy test', function () {
    expect(pickFilter).toBeTruthy();
  });

  it('should accept filter name as a argument', function () {
    var res = pickFilter('UPPER', 'lowercase');

    expect(res).toBe('upper');
  });

  it('should accept array of filters names as argument', function () {
    var res = pickFilter('UPPER', ['lowercase', 'uppercase']);

    expect(res).toBe('UPPER');
  });

  it('should accept object notation of filter definition', function () {
    var res = pickFilter([1, 2, 3], {name: 'limitTo', args: [2]});

    expect(res).toEqual([1, 2]);
  });

  it('should accept object notation of filter inside array', function () {
    var date = new Date('21 May 2015 10:00');
    var res = pickFilter(date, [{name: 'date', args: ['MMMM']}, 'uppercase']);

    expect(res).toBe('MAY');
  });

  it('should return value as-is if no filter specified', function () {
    var res = pickFilter('UPPER');
    expect(res).toBe('UPPER');
  });
});
