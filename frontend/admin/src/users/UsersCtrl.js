const dependencies = ['ui.router'];

export default angular.module('boss.admin.UsersCtrl', dependencies)
  .controller('UsersCtrl', function UsersCtrl($scope, $filter, usersData, $state, userRoles) {
    $scope.pages = Math.ceil(parseInt(usersData.total) / parseInt(usersData.perPage));
    $scope.roles = userRoles;
    $scope.gridConfig = {
      data: usersData,
      uniqueField: 'user_id',
      link: {
        sref: 'users.details',
        idField: 'user_id'
      },
      columns: [
        {field: 'name', title: $filter('translate')('Name')},
        {field: 'roleInfo', title: $filter('translate')('Role'), filter: 'localizedName'},
        {field: 'email', title: 'E-mail'}
      ]
    };
    $scope.searchTags = [];
    var roleFilter = {
      property: 'role', title: $filter('translate')('Role'), options: []
    };
    roleFilter.options = userRoles.map(role => {
      return {text: $filter('localizedName')(role), val: role.role_id};
    });
    $scope.filters = [
      roleFilter,
      {
        property: 'visibility', title: $filter('translate')('Status'),
        options: [
          {text: $filter('translate')('Active'), val: 'visible'},
          {text: $filter('translate')('In archive'), val: 'deleted'}
        ]
      }
    ];
  });
