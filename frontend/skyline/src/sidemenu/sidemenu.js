const dependencies = ['boss.const'];

export default angular.module('skyline.SidemenuCtrl', dependencies)
  .controller('SidemenuCtrl', function ($scope, $filter, CONST) {
    var menu = [
      {sref: 'openstack.simple', title: $filter('translate')('Servers')},
      {sref: 'openstack.images', title: $filter('translate')('ISO Images')},
      {sref: 'openstack.ptr', title: $filter('translate')('PTR')}
    ];

    if (CONST.floating_ips) {
      menu.push({sref: 'openstack.ips', title: $filter('translate')('IP-addresses')});
    }

    menu.push({sref: 'openstack.backup.list', title: $filter('translate')('Backup')});

    if (CONST.dns) {
      menu.push({sref: 'openstack.dns.domains', title: $filter('translate')('DNS')});
    }

    $scope.menu = menu;
  });
