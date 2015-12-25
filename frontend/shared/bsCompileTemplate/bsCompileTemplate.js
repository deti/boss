const dependencies = [];

export default angular.module('boss.compileTemplate', dependencies)
  .directive('bsCompileTemplate', function ($compile) {
    return function (scope, element, attrs) {
      scope.$watch(
        function (scope) {
          return scope.$eval(attrs.bsCompileTemplate);
        },
        function (value) {
          element.html(value);
          $compile(element.contents())(scope);
        }
      );
    };
  });

/**
 * @ngdoc directive
 * @name boss.compileTemplate.directive:bsCompileTemplate
 *
 * @description
 * Compile template from variable
 *
 * @param {expression} bs-compile-template Template to compile
 */
