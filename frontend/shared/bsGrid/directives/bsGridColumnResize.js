const dependencies = [];

export default angular.module('boss.grid.columnResize', dependencies)
  .directive('bsGridColumnResize', function ($window, $rootScope) {
    const $win = angular.element($window);
    return {
      restrict: 'E',
      require: '^bsGrid',
      scope: {
        column: '='
      },
      link(scope, element, attrs, bsGridCtrl) {
        const column = element.parent();
        const elWidth = 10;
        element.on('mousedown', onColumnResize);
        element.on('click', e => { // prevent sorting on click
          e.preventDefault();
          e.stopPropagation();
        });
        function onColumnResize (e) {
          e.stopPropagation();
          e.preventDefault();
          element.addClass('active');

          var newWidth,
            sizerHeight = bsGridCtrl.$element.parent().height(),
            initialX = e.pageX,
            initialWidth = column.outerWidth() - elWidth;
          $win.on('mousemove', mousemove);
          $win.one('mouseup', mouseup);

          element.css({
            right: 'inherit',
            height: sizerHeight,
            left: initialWidth
          });

          function mouseup(e) {
            e.stopPropagation();
            e.preventDefault();
            $win.off('mousemove', mousemove);
            element.removeClass('active');
            element.css({
              right: '',
              height: '',
              left: 'inherit'
            });
            scope.column.width = newWidth;
            $rootScope.$emit(bsGridCtrl.gridId + 'width_update');
            return false;
          }
          function mousemove(e) {
            var currentX = e.pageX,
              diff = currentX - initialX;
            newWidth = initialWidth + diff;
            element.css('left', newWidth);
          }
        }
      }
    };
  });

/**
 * @ngdoc directive
 * @name boss.grid.directive:bsGridColumnResize
 * @restrict E
 *
 * @description
 * Column resizer
 *
 * @param {expression} column
 */
