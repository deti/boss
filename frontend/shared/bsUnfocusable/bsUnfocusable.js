const dependencies = [];

export default angular.module('boss.unfocusable', dependencies)
  .directive('bsUnfocusable', function () {
    return {
      restrict: 'A',
      link: function (scope, $el) {
        $el.on('focus', function () {
          $el.blur();
        });
      }
    };
  });
