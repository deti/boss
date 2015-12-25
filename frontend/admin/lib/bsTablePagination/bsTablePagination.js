const dependencies = ['ui.router'];

export default angular.module('boss.tablePagination', dependencies)
  .directive('bsTablePagination', function ($state, $stateParams) {
    return {
      restrict: 'E',
      template: require('./bsTablePagination.tpl.html'),
      scope: {
        pages: '='
      },
      link: function (scope, elem, attr) {
        console.log(scope.pages);
        scope.currentPage = parseInt($stateParams.page) || 1;
        scope.gap = 5;
        scope.ppages = Math.ceil(parseInt(scope.pages) / scope.gap);

        function calculateStartPage() {
          var startPage = scope.currentPage - Math.floor(scope.gap / 2);
          if (scope.currentPage + Math.floor(scope.gap / 2) > scope.pages) {
            startPage = scope.pages - scope.gap + 1;
          }
          if (startPage <= 0) {
            return 1;
          }
          return startPage;
        }

        scope.startPage = calculateStartPage();

        scope.pageRange = function (size, start, end) {
          if (size < end) {
            end = size + 1;
          }
          return _.range(start, end);
        };

        scope.setPage = function (p) {
          scope.currentPage = p;
          $state.go(attr.stateName, {page: p});
        };
      }
    };
  });
