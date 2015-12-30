const dependencies = [
  require('../bsCompileTemplate/bsCompileTemplate').default.name,
  require('../trustFilter/trustFilter').default.name,
  require('../pickFilter/pickFilter').default.name,
  require('./BsGridCtrl').default.name,
  require('./directives/bsGridStyles').default.name,
  require('./directives/bsGridCell').default.name,
  require('./directives/bsGridHeader').default.name,
  require('./directives/bsGridColumnResize').default.name,
  require('./directives/bsGridExpose').default.name
];

const template = require('./templates/wrapper.tpl.html');

/**
 * @ngdoc directive
 * @name boss.grid.directive:bsGrid
 * @restrict E
 *
 * @description
 * Creates HTML table with responsive design from data and columns definition
 *
 * @param {expression} config
 * @param {String=} type
 */
export default angular.module('boss.grid', dependencies)
  .directive('bsGrid', function () {
    return {
      restrict: 'E',
      require: '?^bsGridExpose',
      controller: 'BsGridCtrl as grid',
      template: template,
      link: function (scope, el, attrs, exposeCtrl) {
        if (exposeCtrl && exposeCtrl.filters) {
          scope.filter = exposeCtrl.filters;
        }
      }
    };
  });



