const dependencies = [];

export default angular.module('boss.domainName', dependencies)
  .directive('bsDomainName', function () {
    function validate(str) { // based on https://github.com/gkaimakas/angular.validators
      /* Remove the optional trailing dot before checking validity */
      if (str[str.length - 1] === '.') {
        str = str.substring(0, str.length - 1);
      }
      var parts = str.split('.');
      var tld = parts.pop();
      if (!parts.length || !/^([a-z\u00a1-\uffff]{2,}|xn[a-z0-9-]{2,})$/i.test(tld)) {
        return false;
      }
      for (var part, i = 0; i < parts.length; i++) {
        part = parts[i];
        if (!/^[a-z\u00a1-\uffff0-9-]+$/i.test(part)) {
          return false;
        }
        if (/[\uff01-\uff5e]/.test(part)) {
          // disallow full-width chars
          return false;
        }
        if (part[0] === '-' || part[part.length - 1] === '-' ||
          part.indexOf('---') >= 0) {
          return false;
        }
      }
      return true;
    }

    return {
      restrict: 'A',
      require: 'ngModel',
      link: function (scope, element, attrs, ctrl) {
        ctrl.$validators.domain = function (modelValue, viewValue) {
          return validate(viewValue);
        };
      }
    };
  });
