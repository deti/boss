const dependencies = [];

export default angular.module('boss.grid.BsGridExpose', dependencies)
  .directive('bsGridExpose', function () {
    return {
      restrict: 'AE',
      controller: function () {
        console.log('ctrl');
        this.filters = [];
      }
    };
  });
