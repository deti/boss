const dependencies = [];

const template = require('../templates/header.tpl.html');

export default angular.module('boss.grid.header', dependencies)
  .directive('bsGridHeader', function () {
    return {
      restrict: 'E',
      require: '^bsGrid',
      template: template
    };
  });

/**
 * @ngdoc directive
 * @name boss.grid.directive:bsGridHeader
 * @restrict E
 */
