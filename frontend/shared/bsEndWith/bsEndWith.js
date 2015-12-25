const dependencies = [];

export default angular.module('boss.endWith', dependencies)
  .directive('bsEndWith', function () {
    return {
      restrict: 'A',
      require: 'ngModel',
      link: function (scope, element, attrs, ctrl) {
        const ending = element.attr('bs-end-with');
        ctrl.$validators.endWith = function (modelValue, viewValue) {
          return _.endsWith(viewValue, ending);
        };
      }
    };
  });
