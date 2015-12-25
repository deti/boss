const dependencies = [];
/**
 * @ngdoc directive
 * @name boss.shared.directive:bsHasError
 * @restrict A
 *
 * @description
 * Check errors in form
 *
 * @param {expression} bs-has-error Custom error condition (error if that true)
 *
 * @example
 <example module="some">
 <file name="template.html">
 <form>
 <div bs-has-error>
 <input type="number" name="someName" class="form-control" ng-model="someName">
 </div>
 <div bs-has-error="additionCondition == true">
 <input type="number" name="someNameTwo" class="form-control" ng-model="someNameTwo">
 </div>
 </form>
 </file>
 </example>
 */
export default angular.module('boss.hasError', dependencies)
  .directive('bsHasError', function () {
    return {
      priority: -1000,
      require: '^form',
      scope: {
        condition: '=bsHasError',
        target: '=hasErrorTarget'
      },
      restrict: 'A',
      link: function (scope, el, attrs, formCtrl) {
        var $inputEl = scope.target ? el.find(scope.target) : el.find('.form-control[name]'),
          modelCtrl = $inputEl.data('$ngModelController');
        if (!modelCtrl) {
          throw 'bs-has-error element has no child input elements that have model controller!';
        }

        var toggleClasses = function (invalid) {
          el.toggleClass('has-error', invalid);
        };
        scope.$watch(function () {
          return (modelCtrl && modelCtrl.$invalid && modelCtrl.$dirty) || (typeof scope.condition !== 'undefined' && scope.condition);
        }, function (invalid) {
          return toggleClasses(invalid);
        });
      }
    };
  });
