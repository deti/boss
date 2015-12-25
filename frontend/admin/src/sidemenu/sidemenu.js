const dependencies = [
  require('../../../shared/localStorage/localStorage').default.name,
  require('../../../shared/appGlobalState/appGlobalState').default.name
];

export default angular.module('boss.admin.sidemenu', dependencies)
  .controller('SideMenuCtrl', function ($scope, $filter, localStorage, $window, appGlobalState) {
    $scope.menu = [
      {sref: 'main', icon: 'customers-v2', title: $filter('translate')('Customers')},
      {sref: 'services', icon: 'services-v2', title: $filter('translate')('Services')},
      {sref: 'flavors', icon: 'dashboard-v2', title: $filter('translate')('VM Templates')},
      {sref: 'tariffs', icon: 'tariffs-v2', title: $filter('translate')('Plans')},
      {sref: 'users', icon: 'users-v2', title: $filter('translate')('Users')},
      //{sref: 'currency', icon: 'currency', title: $filter('translate')('Currency')},
      {sref: 'news', icon: 'notifications-v2', title: $filter('translate')('News')},
      {sref: 'osLogin', icon: 'owner', title: $filter('translate')('Projects')},
      {sref: 'grafana.boss', icon: 'statistics-v2', title: $filter('translate')('Statistic')},
      {sref: 'grafana.openstack', icon: 'cloud-v2', title: $filter('translate')('OS Statistics')},
      {sref: 'openstackUsage', icon: 'transactions-v2', title: $filter('translate')('OS Resources')}
    ];
    appGlobalState.sidemenuWide = localStorage.getItem('sideMenuWide', $window.innerWidth >= 1280);
    $scope.wide = appGlobalState.sidemenuWide;
    $scope.toggleWide = function (event) {
      //$scope.wide = !$scope.wide;
      $scope.wide = !appGlobalState.sidemenuWide;
      appGlobalState.sidemenuWide = $scope.wide;
      localStorage.setItem('sideMenuWide', appGlobalState.sidemenuWide);

    };
    $scope.globalState = appGlobalState;
  });
