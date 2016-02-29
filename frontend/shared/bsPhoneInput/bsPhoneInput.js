const dependencies = [];

export default angular.module('boss.phoneInput', dependencies)
  .directive('bsPhoneInput', function () {
    return {
      require: 'ngModel',
      link: function (scope, el, attr, modelCtrl) {
        modelCtrl.$parsers.push(function (viewValue) {
          if (viewValue) {
            var newViewValue = viewValue.replace(/[^0-9]/g, '').slice(0, 11);

            if (_.startsWith(viewValue, '+')) {
              modelCtrl.$setValidity('minPhoneLength', newViewValue.length > 10);
              newViewValue = '+' + newViewValue;
            } else {
              modelCtrl.$setValidity('minPhoneLength', newViewValue.length > 4);
            }

            if (newViewValue !== viewValue) {
              modelCtrl.$setViewValue(newViewValue);
              modelCtrl.$render();
            }
            return newViewValue;
          } else {
            modelCtrl.$setValidity('minPhoneLength', true);
            return null;
          }
        });
      }
    };
  });
