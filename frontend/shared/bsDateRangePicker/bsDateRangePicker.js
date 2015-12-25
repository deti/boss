const dependencies = [
  'mgcrea.ngStrap.datepicker',
  'angular-click-outside',
  require('./datePickerViewProvider').default.name
];

/**
 * @ngdoc directive
 * @name boss.shared.directive:bsDateRangePicker
 * @restrict E
 *
 * @description
 * Create calendar icon than allow to chose date range
 *
 * @param {number} start-date Start date in milliseconds
 * @param {number} end-date End date in milliseconds
 * @param {function} on-change Callback when date range was changed
 */
export default angular.module('boss.dateRangePicker', dependencies)
  .directive('bsDateRangePicker', function () {
    return {
      restrict: 'E',
      template: require('./bsDateRangePicker.tpl.html'),
      scope: {
        startDate: '=',
        endDate: '=',
        onChange: '&'
      },
      link: function (scope, element, attrs) {
        var startDateChanged = false,
          endDateChanged = false;
        scope.visible = false;
        scope.toggleVisible = function () {
          scope.visible = !scope.visible;
          if (!scope.visible) {
            startDateChanged = false;
            endDateChanged = false;
            scope.onChange();
          }
        };
        scope.hide = function () {
          scope.visible = false;
        };
        scope.$watch('startDate', function () {
          if (!scope.visible) {
            return;
          }
          startDateChanged = true;
          isNeedToUpdate();
        });
        scope.$watch('endDate', function () {
          if (!scope.visible) {
            return;
          }
          endDateChanged = true;
          isNeedToUpdate();
        });
        function isNeedToUpdate() {
          if (startDateChanged && endDateChanged) {
            scope.toggleVisible();
          }
        }
      }
    };
  });
