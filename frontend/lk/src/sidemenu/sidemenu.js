const dependencies = [
  require('../../../shared/localStorage/localStorage').default.name
];

export default angular.module('boss.lk.sidemenu', dependencies)
  .controller('SidemenuCtrl', function ($scope, $filter, localStorage, $window, CONST, $rootScope, $state, userInfo) {
    $scope.beta = CONST.local.region === 'prod';

    $scope.menu = [
      {sref: 'main', icon: 'dashboard-v2', title: $filter('translate')('Main')}
    ];
    var horizonMenuItem = {sref: 'horizon', icon: 'cloud-v2', title: $filter('translate')('My cloud')};
    var skylineMenuItem = {
      sref: 'openstack', icon: 'cloud-v2', title: $filter('translate')('My cloud'), submenu: [
        {sref: 'openstack.servers.list', title: $filter('translate')('Servers')},
        {sref: 'openstack.images', title: $filter('translate')('Images')},
        {sref: 'openstack.volumes', title: $filter('translate')('Disks')}
      ]
    };
    if (CONST.local.skyline.floating_ips) {
      skylineMenuItem.submenu.push({sref: 'openstack.ips', title: $filter('translate')('IP-addresses')});
    }

    skylineMenuItem.submenu.push({sref: 'openstack.backup.list', title: $filter('translate')('Backup')});

    if (CONST.local.skyline.dns) {
      skylineMenuItem.submenu.push({sref: 'openstack.dns.domains', title: $filter('translate')('DNS')});
      skylineMenuItem.submenu.push({sref: 'openstack.ptr', title: $filter('translate')('PTR')});
    }

    switch (userInfo.os_dashboard) {
      case 'horizon':
        $scope.menu.push(horizonMenuItem);
        break;
      case 'skyline':
        $scope.menu.push(skylineMenuItem);
        break;
      default:
        $scope.menu.push(skylineMenuItem);
        horizonMenuItem.title = 'Horizon';
        skylineMenuItem.submenu.push(horizonMenuItem);
    }
    $scope.menu = $scope.menu.concat([
      {sref: 'services', icon: 'services-v2', title: $filter('translate')('Services')},
      {sref: 'statistics', icon: 'statistics-v2', title: $filter('translate')('Statistics')},
      {sref: 'transactions', icon: 'transactions-v2', title: $filter('translate')('Transactions')},
      {sref: 'support', icon: 'support-v2', title: $filter('translate')('Support')},
      {sref: 'news', icon: 'news-v2', title: $filter('translate')('News')}
    ]);

    $scope.wide = localStorage.getItem('sideMenuWide', $window.innerWidth >= 1280);
    $scope.toggleWide = function () {
      $scope.wide = !$scope.wide;
      localStorage.setItem('sideMenuWide', $scope.wide);
    };

    function shouldShowSubmenu() {
      var activeMenuItem = _.find($scope.menu, function (item) {
        return $state.includes(item.sref);
      });

      $scope.submenu = activeMenuItem !== undefined && !!activeMenuItem.submenu;
    }

    $rootScope.$on('$stateChangeSuccess', function () {
      shouldShowSubmenu();
    });
    shouldShowSubmenu();
  });
