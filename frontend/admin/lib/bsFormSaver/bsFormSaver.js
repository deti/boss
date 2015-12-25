export default angular.module('boss.formSaver', [])
  .directive('bsFormSaver', function ($compile, $timeout, $document) {
    const templateStr = require('./bsFormSaver.tpl.html');
    function forEachProperty(controller, fn) {
      for (var key in controller) {
        if (controller.hasOwnProperty(key) && String(key).charAt(0) !== '$' && angular.isObject(controller[key])) {
          fn(key);
        }
      }
    }

    return {
      require: 'form',
      link: function (scope, element, attrs, formController) {
        var $body = angular.element($document[0].body),
          $fakeButton = angular.element('<button style="display: none;" type="submit"></button>');
        scope.oldValues = {};
        scope.changed = [];
        scope.formController = formController;
        scope.showChangeLog = false;
        scope.cancel = restoreValues;
        scope.submit = function () {
          $timeout(function () {
            $fakeButton.click();
          });
        };

        element.on('submit', function () {
          scope.changed = [];
          forEachProperty(formController, key => {
            formController[key].$setPristine();
            setOldValue(key);
          });
        });

        $timeout(function () {
          forEachProperty(formController, key => {
            scope.$watch(`formController['${key}'].$dirty`, _.after(2, function (isDirty) {
              if (isDirty && scope.changed.indexOf(key) === -1) {
                scope.changed.push(key);
              }
            }));
            setOldValue(key);
          });
        });

        var template = $compile(templateStr)(scope);
        $body.append(template);
        element.append($fakeButton);

        scope.$on('$destroy', function () {
          template.detach();
        });

        function restoreValues() {
          forEachProperty(formController, key => {
            var val = _.isObject(scope.oldValues[key]) ? _.cloneDeep(scope.oldValues[key]) : scope.oldValues[key];
            formController[key].$rollbackViewValue();
            formController[key].$setViewValue(val);
            formController[key].$commitViewValue();
            if (!val && formController[key].$dateValue) {
              formController[key].$dateValue = val;
            }
            formController[key].$render();
            formController[key].$setPristine();
            formController[key].$dirty = false;
          });
          scope.changed = [];
        }

        function setOldValue(key) {
          $timeout(() => {
            if (formController[key].$dateValue) { // for angular-strap datepicker use viewValue instead of modelValue.
              scope.oldValues[key] = formController[key].$viewValue;
            } else {
              scope.oldValues[key] = _.isObject(formController[key].$modelValue) ? _.cloneDeep(formController[key].$modelValue) : formController[key].$modelValue;
            }
          });
        }
      }
    };
  });

/**
 * @ngdoc directive
 * @name boss.admin.directive:bsFormSaver
 * @element form
 *
 * @description
 * Save base state of all inputs inside form, then when something will be changed, will be displaed "Save changes" popup.
 *
 * @param {function} ng-submit Submit callback
 *
 * @example
 <example module="some">
 <file name="controller.js">
 angular.module('some', [])
 .controller('AppCtrl', function ($scope) {
    $scope.updateForm = function (form) {
      console.log(form);
      console.log(form.someInput);
    };
  });
 </file>
 <file name="template.html">
 <form name="someForm" bs-form-saver ng-submit="updateForm(someForm)">
 <input type="text" name="someInput" ng-model="someInput">
 </form>
 </file>
 </example>
 */
