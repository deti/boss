const dependencies = [
  require('./server.vncCtrl').default.name
];

export default angular.module('skyline.servers.vnc.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.servers.vnc', {
        url: '/vnc/{id}',
        views: {
          'main@boss': {
            controller: 'OSServersVNCCtrl',
            template: require('./server.vnc.tpl.html')
          }
        },
        data: {
          pageTitle: 'VNC-console',
          bodyClassname: 'mainview-full-height g-horizon'
        },
        resolve: {
          server: function ($stateParams, osServices) {
            return osServices.Nova.server($stateParams.id);
          },
          vncConsole: function (server) {
            return server.vncConsole();
          }
        }
      });
  });
