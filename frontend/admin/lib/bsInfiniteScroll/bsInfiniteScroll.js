import 'ng-infinite-scroll/build/ng-infinite-scroll';

const dependencies = [
  'infinite-scroll',
  require('../../src/const/const').default.name
];

export default angular.module('boss.infiniteScroll', dependencies)
  .directive('bsInfiniteScroll', function ($injector, CONST) {
    return {
      restrict: 'E',
      template: require('./bsInfiniteScroll.tpl.html'),
      transclude: true,
      scope: {
        data: '=data',
        total: '@total',
        perPage: '@perPage',
        container: '@container',
        serviceName: '@serviceName',
        method: '@method',
        params: '=params',
        onElementFunction: '&?'
      },
      link: function (scope) {
        var pages = scope.perPage ? (Math.ceil(parseInt(scope.total) / parseInt(scope.perPage))) : 0;
        var currentPage = 1;

        var service = $injector.get(scope.serviceName);

        scope.getNextPage = function () {
          if (currentPage >= pages) {
            return;
          }
          currentPage = currentPage + 1;
          service[scope.method](angular.extend({}, {limit: CONST.pageLimit, page: currentPage}, scope.params))
            .then(function (rsp) {
              rsp.forEach(item => {
                if (scope.onElementFunction) {
                  scope.onElementFunction({element: item});
                }
                scope.data.push(item);
              });
            });
        };
      }
    };
  });

angular.module('infinite-scroll').value('THROTTLE_MILLISECONDS', 250);
