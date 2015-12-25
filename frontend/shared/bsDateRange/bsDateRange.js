const dependencies = [
  'ui.router',
  'pascalprecht.translate',
  require('../bsDateRangePicker/bsDateRangePicker').default.name
];

import constants from '../constants/constants';

/**
 * @ngdoc directive
 * @name boss.shared.directive:bsDateRange
 * @restrict E
 *
 * @description
 * Create panel that allow to display table data in time range
 *
 * @param {string=} class Custom css class
 * @param {Date=} startDate
 * @param {Date=} endDate
 * @param {[{title: string, range: Number}]=}
 */
export default angular.module('boss.dateRange', dependencies)
  .directive('bsDateRange', function ($filter, $state, $stateParams) {
    function afterDate(last) {
      var time = Math.round(new Date().getTime() / 1000);
      return time - last;
    }

    return {
      restrict: 'E',
      template: require('./bsDateRange.tpl.html'),
      scope: {
        startDate: '=?',
        endDate: '=?',
        range: '=?',
        afterParam: '=?',
        beforeParam: '=?',
        resetTime: '=?',
        defaultRange: '=?'
      },
      link: function (scope) {
        if (!scope.range) {
          scope.range = [
            {title: $filter('translate')('week'), range: constants.week},
            {title: $filter('translate')('2 weeks'), range: constants.week * 2},
            {title: $filter('translate')('month'), range: constants.month},
            {title: $filter('translate')('year'), range: constants.year}
          ];
        }

        if (scope.defaultRange) {
          scope.range.push({title: $filter('translate')('all time'), range: 0});
        }

        scope.afterParam = scope.afterParam || 'after';
        scope.beforeParam = scope.beforeParam || 'before';
        scope.resetTime = scope.resetTime || false;

        if ($stateParams[scope.afterParam]) {
          scope.startDate = new Date($stateParams[scope.afterParam] * 1000);
          scope.startDateApplied = scope.startDate;
        }
        if ($stateParams[scope.beforeParam]) {
          scope.endDate = new Date($stateParams[scope.beforeParam] * 1000);
        }
        if (!scope.startDate) {
          scope.startDate = new Date();
          scope.startDate.setMonth(scope.startDate.getMonth() - 1);
          scope.startDateApplied = scope.defaultRange ? '...' : scope.startDate;
        }
        if (!scope.endDate) {
          scope.endDate = new Date();
        }
        scope.endDateApplied = scope.endDate;

        scope.setAfter = function (diff) {
          if (diff) {
            scope.startDate = new Date(afterDate(diff) * 1000);
            scope.endDate = new Date();
            scope.changeRange();
          } else {
            var params = {};
            params[scope.afterParam] = undefined;
            params[scope.beforeParam] = undefined;
            $state.go($state.current.name, params);
          }
        };

        function resetDateTime(date, hours, minutes) {
          var newDate = new Date(date);
          var ts = newDate.setHours(hours, minutes);
          return Math.round(ts / 1000);
        }

        scope.changeRange = function () {
          var params = {};
          params[scope.afterParam] = scope.resetTime ?
                                     resetDateTime(scope.startDate, 0, 1) :
                                     Math.round(scope.startDate.getTime() / 1000);
          params[scope.beforeParam] = scope.resetTime ?
                                      resetDateTime(scope.endDate, 23, 59) :
                                      Math.round(scope.endDate.getTime() / 1000);

          $state.go($state.current.name, params);
          scope.startDateApplied = scope.startDate;
          scope.endDateApplied = scope.endDate;
        };
      }
    };
  });
