const dependencies = [
  require('./RecreateCtrl').default.name
];

export default angular.module('skyline.simple.recreate', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.simple.recreate', {
        url: '/recreate/{id}',
        views: {
          'main@boss': {
            controller: 'RecreateCtrl',
            template: require('./recreate.tpl.html')
          }
        },
        data: {
          pageTitle: 'Recreate server'
        },
        resolve: {
          server: function ($stateParams, osServices, $state) {
            return osServices.Nova.server($stateParams.id)
              .catch(e => {
                $state.go('openstack.simple');
              });
          },
          images: function (osServices) {
            return osServices.Glance.images();
          }
        }
      });
  });
