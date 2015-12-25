import './passwordGenerator';

describe('passwordGenerator', function () {
  var passwordGenerator,
    alphaChars,
    specialChars,
    numberChars;
  beforeEach(angular.mock.module('passwordGenerator'));

  beforeEach(inject(function (_passwordGenerator_, PASS_ALPHA, PASS_NUMBERS, PASS_SPECIALS) {
    passwordGenerator = _passwordGenerator_;
    alphaChars = PASS_ALPHA;
    specialChars = PASS_SPECIALS;
    numberChars = PASS_NUMBERS;
  }));

  it('should generate password with specified length', function () {
    var pass = passwordGenerator(12);

    expect(pass.length).toBe(12);
  });

  it('should not generate password smaller than 6 symbols', function () {
    var pass = passwordGenerator(1);
    expect(pass.length).toBe(6);
    pass = passwordGenerator(2);
    expect(pass.length).toBe(6);
  });

  it('should generate password that contain 2 special chars, 3 numbers and symbols', function () {
    var pass = passwordGenerator(12);
    var chars = pass.split('');
    var numbersCount = 0,
      specialCount = 0,
      alphaCount = 0;
    chars.forEach(char => {
      if (alphaChars.indexOf(char) !== -1) {
        alphaCount++;
      } else if (specialChars.indexOf(char) !== -1) {
        specialCount++;
      } else if (numberChars.indexOf(char) !== -1) {
        numbersCount++;
      }
    });

    expect(numbersCount).toBe(3);
    expect(specialCount).toBe(2);
    expect(alphaCount).toBe(7);
  });
});
