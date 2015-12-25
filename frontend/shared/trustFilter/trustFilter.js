const dependencies = [];
export default angular.module('boss.trustFilter', dependencies)
  .filter('trust', function ($sce) {
    return function (value, type) {
      return $sce.trustAs(type || 'html', value);
    };
  });
