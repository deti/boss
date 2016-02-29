const dependencies = [
  require('../../openstackService/OSCredentials').default.name,
  require('../../openstackService/Keystone').default.name,
  require('../../openstackService/Nova').default.name,
  require('../../dialog/dialog').default.name
];
const cellAddresses = require('../servers/cell.addresses.partial.tpl.html');
const cellCheckbox = require('./cell.checkbox.tpl.html');
const cellTitle = require('./cell.title.tpl.html');
const confirmTemplate = require('./confirm-alert.tpl.html');

export default angular.module('boss.admin.projects', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('projects', {
        parent: 'boss',
        url: '/projects?owner&projectName',
        params: {
          filterActive: null
        },
        views: {
          'main@boss': {
            controller: 'ProjectsCtrl',
            template: require('./projects.tpl.html')
          }
        },
        data: {
          pageTitle: 'Projects'
        },
        resolve: {
          keystoneAuth(Keystone, $q, $state, $timeout) {
            if (!Keystone.authPair) {
              $timeout(function () {
                $state.go('osLogin');
              }, 0);
              return $q.reject('you need to auth first');
            }
            return Keystone.authPair;
          },
          servers: function (keystoneAuth, Nova, OSCredentials) {
            OSCredentials.tenantId = keystoneAuth.tenantId;
            OSCredentials.token = keystoneAuth.token;
            return Nova.servers(true, 1);
          },
          users: function (keystoneAuth, Keystone) {
            return Keystone.users(keystoneAuth.token);
          },
          projects: function (keystoneAuth, Keystone) {
            return Keystone.projects(keystoneAuth.token);
          }
        }
      });
  })
  .controller('ProjectsCtrl', function ($scope, $filter, $q, servers, projects, users, dialog, $stateParams) {
    var owners = [],
      projectsNames = [];
    servers.forEach(server => {
      server.project = _.find(projects.projects, {id: server.tenant_id});
      server.user = _.find(users.users, {id: server.user_id});
      server.owner = server.metadata.provider || 'MANUAL';
      owners.push(server.owner);
      server.projectName = '-';
      if (server.project) {
        server.projectName = server.project.name;
        projectsNames.push(server.projectName);
      }
    });
    var serversCopy = filterServers();
    var convertToTags = i => {
      return {text: i, val: i};
    };
    owners = _.uniq(owners).map(convertToTags);
    projectsNames = _.uniq(projectsNames).map(convertToTags);
    $scope.servers = serversCopy;
    $scope.columns = [
      {
        template: cellCheckbox,
        width: 45,
        titleClass: 'empty',
        sortable: false,
        cellClass: 'no-padding'
      },
      {
        template: cellTitle,
        cellClass: 'initial-position',
        title: $filter('translate')('Owner')
      },
      {
        field: 'projectName',
        title: $filter('translate')('Project')
      },
      {
        field: 'user.name',
        title: $filter('translate')('Username')
      },
      {
        field: 'name',
        title: $filter('translate')('Server')
      },
      {
        field: 'addresses.ips.length',
        title: $filter('translate')('IP Address'),
        cellClass: 'long-text',
        templateUrl: cellAddresses
      }
    ];

    $scope.serversFilters = [
      {
        property: 'owner', title: $filter('translate')('Owner'),
        options: owners
      },
      {
        property: 'projectName', title: $filter('translate')('Project'),
        options: projectsNames
      }
    ];
    $scope.searchTags = [];

    $scope.remove = function (items) {
      dialog.confirm('', $filter('translate')('Yes'), $filter('translate')('No'), confirmTemplate, {items})
        .then(() => {
          return $q.all(items.map(i => i.remove()));
        })
        .then(() => {
          items.forEach(i => _.remove(serversCopy, i));
          console.log('removed?');
        });
    };
    $scope.selected = [];
    $scope.itemSelectChanged = function () {
      $scope.selected = _.filter(serversCopy, {selected: true});
    };

    function filterServers() {
      var paramsKeys = Object.keys($stateParams);
      return servers.filter(s => {
        for (let i = 0; i < paramsKeys.length; i++) {
          let key = paramsKeys[i];
          if ($stateParams[key] && s.hasOwnProperty(key) && s[key] !== $stateParams[key]) {
            return false;
          }
        }
        return true;
      });
    }
  });
