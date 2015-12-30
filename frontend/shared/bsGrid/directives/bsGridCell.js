const dependencies = [];

const templates = {
  normal: require('../templates/cell.tpl.html'),
  static: require('../templates/cell.static.tpl.html')
};

export default angular.module('boss.grid.cell', dependencies)
  .directive('bsGridCell', function () {
    return {
      restrict: 'A',
      require: '^bsGrid',
      template(el, attrs) {
        if (attrs.bsGridCell) {
          return templates[attrs.bsGridCell];
        }
        return templates.normal;
      }
    };
  });

/**
 * @ngdoc directive
 * @name boss.grid.directive:bsGridCell
 * @restrict A
 *
 * @description
 *
 * @param {String=} bsGridCell
 */
