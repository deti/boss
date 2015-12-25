export default angular.module('skyline.servers.vncCtrl', [])
  .controller('OSServersVNCCtrl', function OSServersVNCCtrl($scope, server, vncConsole, $sce) {
    $scope.trustSrc = function (src) {
      return $sce.trustAsResourceUrl(src);
    };
    $scope.consoleUrl = vncConsole.console.url;
  });
