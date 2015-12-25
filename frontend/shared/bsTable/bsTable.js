const dependencies = [
  'ui.router',
  require('../trustFilter/trustFilter').default.name,
  require('../appGlobalState/appGlobalState').default.name,
  require('./TableColumn').default.name,
  require('../bsCompileTemplate/bsCompileTemplate').default.name,
  require('../pickFilter/pickFilter').default.name,
  require('./bsTableCell').default.name
];

const headerPartialPath = require('./tableHeader.partial.tpl.html');
const cellPartialPath = require('./cell.partial.tpl.html');
const staticCellPartialPath = require('./cell.static.partial.tpl.html');
const cellWrapperPartialPath = require('./cellWrapper.partial.tpl.html');


/**
 * @ngdoc directive
 * @name boss.table.directive:bsTable
 * @restrict E
 *
 * @description
 * Creates HTML table with responsive design from data and columns definition
 *
 * @param {Array} data Table data
 * @param {expression} columns Columns definition. It must be instances of TableColumn or objects, that will be passed to TableColumn constructor
 * @param {string=} id-field Name of field in data, used as unique identifier (used for links). Defaults to 'id'
 * @param {string} sref Name of the details state
 * @param {boolean=} simple Use simple template. Simple template doesn't have responsive features and scrolling
 * @param {string=} empty-placeholder Placeholder for empty table. Defaults to 'Нет данных'.
 * @param {expression=} action Template url to show on cell click
 * @param {boolean=} srefPushToLocation Should ui-sref push target location to url
 * @param {boolean=} static Use static cell template
 * @param {boolean=} scroll
 */
export default angular.module('boss.table', dependencies)
  .directive('bsTable', function ($window, $rootScope, $timeout, $state) {
    const templates = {
      bsTableWithActions: require('./bsTableWithActions.tpl.html'),
      bsTableSimpleScroll: require('./bsTableSimpleScroll.tpl.html'),
      bsTableSimple: require('./bsTableSimple.tpl.html'),
      bsTable: require('./bsTable.tpl.html')
    };
    return {
      restrict: 'E',
      scope: true,
      template: function (elem, attrs) {
        var templateName = attrs.simple ? (attrs.action ? 'bsTableWithActions' : (attrs.scroll ? 'bsTableSimpleScroll' : 'bsTableSimple')) : 'bsTable';
        return templates[templateName];
      },
      controller: 'TableCtrl',
      link: function (scope, element, attrs) {
        scope.headerPartialPath = headerPartialPath;
        scope.cellWrapperPartialPath = cellWrapperPartialPath;
        const tableColumnWidthStoppers = {
          1366: 1,
          1500: 2,
          1800: 3,
          2300: 4
        };
        const tableColumnWidthStoppersSidemenu = {
          1500: 1,
          1800: 2,
          2100: 3,
          2400: 4
        };
        var isSimpleTable = !!attrs.simple;
        var $win = angular.element($window),
          columnsWithWidth = [];

        var cancelListener = $rootScope.$on('$stateChangeSuccess', updateColumnWidth);
        scope.$on('$destroy', cancelListener);
        if (!isSimpleTable) {
          $win.on('resize', _.throttle(function () {
            updateColumnWidth();
            scope.$apply();
          }, 100));
          scope.$watch('globalState.detailsWide', updateColumnWidth);
          scope.$watch('globalState.detailsVisible', updateColumnWidth);
        }

        $timeout(() => {
          scope.afterRedraw = $state.current.name;
          updateColumnWidth();
        });

        scope.onColumnResize = onColumnResize;

        scope.columnsCount = 0;
        function updateColumnWidth () {
          $timeout(() => {
            scope.afterRedraw = _.random(0, 100);
          });
          scope.afterRedraw = $state.current.name;
          var columnsCount = scope.columns.length,
            tableWidth = element.parent().width(),
            equalsColumnsWidth = tableWidth,
            winWidth = $win.width();

          if (!isSimpleTable && scope.globalState.detailsVisible) {
            _.forEach(Object.keys(scope.globalState.menuWide ? tableColumnWidthStoppersSidemenu : tableColumnWidthStoppers), width => {
              if (winWidth <= width) {
                columnsCount = tableColumnWidthStoppers[width];
                return false;
              }
            });
            if (scope.globalState.detailsWide) {
              columnsCount -= 1;
            }
          }
          scope.columnsCount = columnsCount;
          if (!isSimpleTable && scope.globalState.detailsVisible) {
            columnsWithWidth = [];
          } else {
            columnsWithWidth = _.take(scope.columns, columnsCount)
              .filter(item => item.width);
            columnsWithWidth
              .forEach(item => equalsColumnsWidth -= parseInt(item.width));
          }
          scope.columnWidth = (equalsColumnsWidth / tableWidth) * 100 / (columnsCount - columnsWithWidth.length);
          scope.columnsCount = columnsCount;
        }

        function onColumnResize (e) {
          e.stopPropagation();
          e.preventDefault();
          e.originalEvent.preventDefault();
          var $target = angular.element(e.target),
            $th = $target.parent('th');
          if ($th.length === 0) {
            $th = $target.parent('td');
          }
          $target.addClass('active');

          var newWidth,
            lPadding = parseInt($th.css('padding-left')),
            sizerHeight = element.find('.table-body').height() + $target.height(),
            initialX = e.pageX,
            initialWidth = $th.outerWidth() - lPadding;
          $win.on('mousemove', mousemove);
          $win.one('mouseup', mouseup);

          $target.css({
            right: 'inherit',
            height: sizerHeight,
            left: initialWidth
          });

          function mouseup(e) {
            e.stopPropagation();
            e.preventDefault();
            $win.off('mousemove', mousemove);
            $target.removeClass('active');
            $target.css({
              right: '',
              height: '',
              left: 'inherit'
            });
            scope.columns[$th.index()].width = newWidth;
            updateColumnWidth();
            scope.$apply();
            return false;
          }
          function mousemove(e) {
            var currentX = e.pageX,
              diff = currentX - initialX;
            newWidth = initialWidth + lPadding + diff;
            $target.css('left', newWidth);
          }
        }

        scope.cellTemplate = attrs.static ? staticCellPartialPath : cellPartialPath;
      }
    };
  })
  .controller('TableCtrl', function ($scope, $element, $attrs, TableColumn, $filter, appGlobalState) {
    $scope.idField = $attrs.idField || 'id';
    $scope.sref = $attrs.sref;
    $scope.srefPushToLocation = !!$attrs.srefPushToLocation;
    $scope.dataName = $attrs.data;
    $scope.actionsTemplate = $scope.$eval($attrs.action);
    $scope.globalState = appGlobalState;
    $scope.columns = $scope.$eval($attrs.columns).map(item => {
      if (item instanceof TableColumn) {
        return item;
      }
      return new TableColumn(item);
    });
    $scope.emptyPlaceholder = $attrs.emptyPlaceholder || $filter('translate')('No data');
    $scope.getValue = function (name) {
      return $scope.$eval(name);
    };
    $scope.keepActiveItem = {
      value: false
    };
    $scope.showActions = function (item) {
      if (!$scope.keepActiveItem.value) {
        $scope.activeItem = item;
      }
    };
    $scope.hideActions = function () {
      if (!$scope.keepActiveItem.value) {
        $scope.activeItem = false;
      }
    };
  });
