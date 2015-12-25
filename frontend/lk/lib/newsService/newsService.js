const dependencies = ['restangular'];

export default angular.module('boss.newsService', dependencies)
  .factory('newsService', function (Restangular) {
    var News = Restangular.all('news');

    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'news') {
        if (operation === 'getList') {
          data = data.news_list.items;
        }
      }
      return data;
    });

    return {
      getList: function (args) {
        return News.getList(args);
      }
    };
  });
