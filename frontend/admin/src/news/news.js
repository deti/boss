const dependencies = [
  require('../../lib/newsService/newsService').default.name,
  require('./NewsCtrl').default.name,
  require('./details/news.details').default.name,
  require('./new/news.new').default.name
];

export default angular.module('boss.admin.news', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('news', {
        parent: 'boss',
        url: '/news?text&page',
        params: {
          filterActive: null
        },
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
          newsData: function (newsService, $stateParams) {
            return newsService.getList(angular.extend({}, {visible: true, limit: 50}, $stateParams));
          }
        }
      });
  });
