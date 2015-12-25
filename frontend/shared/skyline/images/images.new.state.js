const dependencies = [
  require('./images.newCtrl').default.name
];

export default angular.module('skyline.images.new.state', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('openstack.images.new', {
        url: '/new',
        views: {
          'main@boss': {
            controller: 'OSImagesNewCtrl',
            template: require('./new.tpl.html')
          }
        },
        data: {
          pageTitle: 'Images'
        },
        resolve: {}
      });
  });
