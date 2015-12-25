const dependencies = [];

export default angular.module('boss.admin.layout', dependencies)
  .controller('LayoutCtrl', function ($scope, $window) {
    var $win = angular.element($window);
    $win.on('resize', _.throttle(function () {
      $scope.windowHeight = $win.height();
      $scope.$apply();
    }, 100));
  });
