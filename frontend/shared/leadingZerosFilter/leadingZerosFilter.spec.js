import './leadingZerosFilter';

describe('Test leadingZeros filter', function () {
  var leadingZeroFilter;
  beforeEach(angular.mock.module('boss.leadingZerosFilter'));
  beforeEach(inject(function ($filter) {
    leadingZeroFilter = $filter('leadingZeros');
  }));

  it('should add leading zeros', function () {
    expect(leadingZeroFilter('1', 2)).toEqual('01');
    expect(leadingZeroFilter('68', 4)).toEqual('0068');
  });
  it('should add 2 zeros by default', function () {
    expect(leadingZeroFilter(1)).toEqual('01');
  });
});
