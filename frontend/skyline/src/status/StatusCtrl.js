const dependencies = [
  require('../../../shared/skyline/servers/server.listCtrl').default.name,
  require('../../../shared/skyline/servers/server.vns.state').default.name
];

export default angular.module('skyline.StatusCtrl', dependencies)
  .value('serverActionsTpl', require('./cell.actions.partial.tpl.html'))
  .controller('StatusCtrl', function StatusCtrl($controller, $scope, servers, osServices) {
    angular.extend(this, $controller('OSServersListCtrl', {
      $scope,
      osServices,
      servers
    }));
    _.remove($scope.columns, {field: 'volumeSize'});
  });
