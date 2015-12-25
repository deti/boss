const dependencies = ['pascalprecht.translate'];
/**
 * @ngdoc directive
 * @name boss.validateHint.directive:bsValidateHint
 * @restrict a
 *
 * @description
 * Show error hint to user
 *
 * @param {expression} bsValidateHint Key-value object
 */
export default angular.module('boss.validateHint', dependencies)
  .directive('bsValidateHint', function ($filter) {
    return {
      priority: -1000,
      require: '^ngModel',
      link: function (scope, el, attrs, ngModel) {
        var opts = angular.extend({
            required: $filter('translate')('This field is mandatory'),
            email: $filter('translate')('Enter a correct email address'),
            minPhoneLength: $filter('translate')('Insufficient number length'),
            number: $filter('translate')('Must be a number'),
            strongPassword: $filter('translate')('Enter a stronger password')
          }, scope.$eval(attrs.bsValidateHint) || {}),
            errCount = 1,
            errContainer,
            afterEl;

        if (el.is('select') && el.parent().hasClass('select')) {
          afterEl = el.parent();
        } else {
          afterEl = el;
        }
        errContainer = afterEl.after('<p class="errorMessage"></p>').next();

        function updateErrors() {
          var errorMessage = [];
          for (var key in ngModel.$error) {
            if (ngModel.$error.hasOwnProperty(key) && ngModel.$error[key] && opts.hasOwnProperty(key)) {
              errorMessage.push(opts[key]);
            }
            if (key === 'server') {
              errorMessage.push(ngModel.$server_error);
            }
          }
          errCount = errorMessage.length;
          errorMessage = errorMessage.join('<br/>');

          errContainer.html(errorMessage);
        }
        el.on('blur', updateErrors);
        scope.$watch(function () {
          return ngModel.$error;
        }, function () {
          if (errCount > 0 || ngModel.$error.server) {
            updateErrors();
          }
        }, true);
      }
    };
  });
