const dependencies = [];

export default angular.module('boss.grid.styles', dependencies)
  .directive('bsGridStyles', function ($rootScope, $document) {
    function generateStyles(columns) {
      return columns
        .map(c => {
          if (c.width) {
            return `.${c.id} {min-width: ${c.width}px;max-width: ${c.width}px;}`;
          }
          return `.${c.id} {flex: 1 0;}`;
        })
        .join('');
    }

    return {
      restrict: 'E',
      require: '^bsGrid',
      link(scope, el, attrs, /* BsGridCtrl */gridCtrl) {
        var styleElement = false;
        function applyStyles() {
          const styles = generateStyles(gridCtrl.columns);
          if (styleElement) {
            styleElement.remove();
          }
          styleElement = angular.element(`<style type="text/css">${styles}</style>`).appendTo($document[0].head);
        }
        scope.$on('$destroy', function () {
          styleElement.remove();
        });
        applyStyles();
        $rootScope.$on(gridCtrl.gridId + 'width_update', applyStyles);
      }
    };
  });
