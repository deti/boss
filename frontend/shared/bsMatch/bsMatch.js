const dependencies = [];
/**
 * @ngdoc directive
 * @name boss.lk.directive:bsMatch
 * @restrict A
 *
 * @description
 * Look at some input by ng-model name, waiting while value will be the same.
 *
 * @param {string} bs-match Input ng-model name
 *
 * @example
 <example module="some">
 <file name="template.html">
 <form name="someForm">
  <input type="text" name="textOne" ng-model="textOne" />
  <input type="text" name="textTwo" ng-model="textTwo" bs-match="textOne" />
  <div ng-if="someForm.$error.match">
    Inputs mismatch
  </div>
 </form>
 </file>
 </example>
 */
export default angular.module('boss.match', dependencies)
  .directive('bsMatch', function () {
    return {
      require: 'ngModel',
      restrict: 'A',
      link: function (scope, element, attrs, ctrl) {
        var matching = element.attr('bs-match');
        ctrl.$validators.match = function (modelValue, viewValue) {
          return viewValue === scope.$eval(matching);
        };
      }
    };
  });
