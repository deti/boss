const dependencies = [];

export default angular.module('boss.admin.grafana', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('grafana', {
        parent: 'boss',
        url: '/statistics',
        views: {
          'main@boss': {
            template: require('./grafana.tpl.html')
          }
        },
        data: {
          pageTitle: 'Statistic'
        }
      })
      .state('grafana.boss', {
        url: '/boss',
        views: {
          'iframe': {
            template: require('./grafana.boss.tpl.html')
          }
        }
      })
      .state('grafana.openstack', {
        url: '/os',
        views: {
          'iframe': {
            template: require('./grafana.openstack.tpl.html')
          }
        }
      });
  });
