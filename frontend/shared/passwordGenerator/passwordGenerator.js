const dependencies = [];

export default angular.module('passwordGenerator', dependencies)
  .constant('PASS_SPECIALS', '!@#$%^&*()_+{}<>?|[]/~')
  .constant('PASS_NUMBERS', '0123456789')
  .constant('PASS_ALPHA', 'abcdefghijklmnopqrstuvwxyz')
  .factory('passwordGenerator', function (PASS_ALPHA, PASS_NUMBERS, PASS_SPECIALS) {
    function generatePass(length = 6) {
      var specialChars = PASS_SPECIALS.split(''),
        numberChars = PASS_NUMBERS.split(''),
        alphaChars = PASS_ALPHA.split('');

      var specialLength = 2,
        numbersLength = 3,
        alphaLength = length - 1 - specialLength - numbersLength;

      var passwordArr = _.sample(specialChars, specialLength)
        .concat(_.sample(numberChars, numbersLength))
        .concat(_.sample(alphaChars, alphaLength));

      passwordArr = _.shuffle(passwordArr);
      passwordArr.unshift(_.sample(alphaChars)[0]);
      return passwordArr.join('');
    }

    return generatePass;
  });
