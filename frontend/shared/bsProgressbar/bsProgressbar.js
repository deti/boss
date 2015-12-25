const dependencies = [];

export default angular.module('boss.progressbar', dependencies)
  .run(function ($templateCache) {
    $templateCache.put('template/progressbar/progressbar.html', require('./progressbar.tpl.html'));
  })
  .directive('bsProgressbar', function () {
    return {
      template: require('./bsProgressbar.tpl.html'),
      restrict: 'E',
      scope: {
        title: '@',
        value: '=',
        max: '='
      }
    };
  });
