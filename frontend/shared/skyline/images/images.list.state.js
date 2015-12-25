const dependencies = [
  require('./images.listCtrl').default.name
];

export default angular.module('skyline.images.list.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.images', {
        url: 'images',
        views: {
          'main@boss': {
            controller: 'OSImagesCtrl',
            template: require('./list.tpl.html')
          }
        },
        data: {
          pageTitle: 'Images'
        },
        resolve: {
          images: function (osServices) {
            return osServices.Glance.images();
          }
        }
      });
  });
