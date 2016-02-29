const dependencies = [];

const cellTpl = require('./cell.tpl.html');

export default angular.module('boss.table.cell', dependencies)
  .directive('bsTableCell', function () {
    return {
      restrict: 'A',
      template: function (el, attrs) {
        return cellTpl;
      }
    };
  });
