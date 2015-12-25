const dependencies = [
  require('./NewsNewCtrl').default.name
];

export default angular.module('boss.admin.news.new', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('news.new', {
        url: '/new',
        views: {
          'details@boss': {
            template: require('./news.new.tpl.html'),
            controller: 'NewsNewCtrl'
          }
        },
        data: {
          detailsVisible: true,
          pageTitle: 'Create news'
        }
      });
  });
