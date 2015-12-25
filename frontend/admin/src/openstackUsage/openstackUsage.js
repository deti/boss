const dependencies = [
  require('../../../shared/reportService/reportService').default.name,
  require('../../../shared/appLocale/appLocale').default.name
];

export default angular.module('boss.admin.openstackUsage', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('openstackUsage', {
        parent: 'boss',
        url: '/openstack/usage',
        views: {
          'main@boss': {
            controller: 'OpenstackUsageCtrl',
            template: require('./openstackUsage.tpl.html')
          }
        },
        data: {
          pageTitle: 'Statistic'
        }
      });
  })
  .controller('OpenstackUsageCtrl', function ($scope, reportService, appLocale) {
    const fields = ['port', 'volumes', 'snapshots', 'floatingip', 'cores', 'gigabytes', 'ram', 'instances', 'server_groups'];
    $scope.usage = false;
    $scope.displayedUsage = [];

    loadUsageData();

    function loadUsageData() {
      reportService.getJSONOpenstackUsage(appLocale.getBackendLocale(true), true)
        .then(function (rsp) {
          $scope.usage = rsp.map(proceedItem);
        });
    }

    function proceedItem(item) {
      item.id = item.tenant;
      fields.forEach(f => {
        item[f] = getValue(item, f);
      });
      return item;
    }

    function getValue(item, field) {
      return (item[field] === null ? '-' : item[field]);
    }
  });
