const dependencies = [];

export default angular.module('boss.leadingZerosFilter', dependencies)
  .filter('leadingZeros', function () {
    return function (input, size = 2) {
      var zero = size - input.toString().length + 1;
      return Array(+(zero > 0 && zero)).join('0') + input;
    };
  });
