const dependencies = [];

export default angular.module('boss.moneyFilter', dependencies)
  .filter('money', function ($filter) {
    return function (value, currency) {
      currency = currency.toUpperCase();
      value = $filter('number')(value);
      var rtn = '';
      if (value.indexOf('-') > -1) {
        rtn = '-';
        value = value.replace('-', '');
      }
      switch (currency) {
        case 'RUB':
          rtn += `${value} <span class="rub">руб.</span>`; // ₽
          break;
        case 'USD':
          rtn += `$${value}`;
          break;
        default:
          rtn += `${value} ${currency}`;
      }
      return rtn;
    };
  });
