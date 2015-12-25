const zxcvbnPath = require('zxcvbn/lib/zxcvbn.js');
const dependencies = [
  require('../../../shared/asynchronousLoader/asynchronousLoader').default.name
];
/**
 * @ngdoc directive
 * @name boss.lk.directive:bsStrongPasswordValidator
 * @restrict A
 * @element input
 *
 * @description
 * Verify password complexity
 *
 * @example
 <example module="some">
 <file name="template.html">
 <form>
 <input type="password"
 ng-model="user.password"
 ng-required="true"
 bs-strong-password-validator
 bs-validate-hint="{strongPassword: 'Chose stronger password'}">
 </div>
 </form>
 </file>
 </example>
 */
export default angular.module('boss.strongPasswordValidator', dependencies)
  .directive('bsStrongPasswordValidator', function (asynchronousLoader) {
    return {
      restrict: 'A',
      require: 'ngModel',
      scope: {
        score: '=bsStrongPasswordValidator'
      },
      link: function (scope, elem, attr, ctrl) {
        scope.score = null;
        scope.ctrl = ctrl;
        scope.$watch('ctrl.$dirty', function (value) {
          if (!value) {
            scope.score = null;
          }
        });
        asynchronousLoader.load(zxcvbnPath).then(function () {
          ctrl.$viewChangeListeners.unshift(function () {
            var res = zxcvbn(ctrl.$viewValue);
            scope.score = res.score;
            ctrl.$setValidity('strongPassword', res.score > -1);
          });
        });
      }
    };
  });
