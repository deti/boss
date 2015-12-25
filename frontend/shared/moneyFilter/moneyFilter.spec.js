import './moneyFilter';

describe('moneyFilter', function () {
  var moneyFilter;
  beforeEach(angular.mock.module('boss.moneyFilter'));
  beforeEach(inject(function (_$filter_) {
    moneyFilter = _$filter_('money');
  }));

  it('try to add currency symbol', function () {
    expect(moneyFilter('5830', 'USD')).toEqual('$5,830');
    expect(moneyFilter('56000', 'RUB')).toEqual('56,000 <span class="rub">руб.</span>');
  });

  it('should properly format money less than 0', function () {
    expect(moneyFilter(-250, 'RUB')).toEqual('-250 <span class="rub">руб.</span>');
    expect(moneyFilter(-250, 'USD')).toEqual('-$250'); // Microsoft Excel use this format
  });

  it('should format number with unknown currency', function () {
    expect(moneyFilter(100, 'EUR')).toEqual('100 EUR');
  });
});
