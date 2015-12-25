const dependencies = [
  require('./NewsCtrl').default.name,
  require('../../lib/newsService/newsService').default.name
];

export default angular.module('boss.lk.news', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('news', {
      parent: 'boss',
      url: '/news',
      views: {
        'main@boss': {
          controller: 'NewsCtrl',
          template: require('./news.tpl.html')
        }
      },
      data: {
        pageTitle: 'News'
      },
      resolve: {
        newsData: function (newsService) {
          return newsService.getList();
        }
      }
    });
  });
