const dependencies = [];

export default angular.module('boss.textPreview', dependencies)
  .factory('textPreview', function () {
    return function (text, symbols = 500) {
      if (text.length < symbols) {
        return {
          main: text,
          rest: ''
        };
      }
      var main = text.substring(0, symbols),
        rest = text.substring(symbols);

      main = main.split(' ');
      rest = main.splice(-1)[0] + rest;
      main = main.join(' ');

      return {
        main,
        rest
      };
    };
  });
