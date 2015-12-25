const dependencies = ['restangular'];

export default angular.module('boss.newsService', dependencies)
  .factory('newsService', function (Restangular) {
    var News = Restangular.all('news');

    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'news') {
        if (operation === 'getList') {
          var extractedData = data.news_list.items;
          extractedData.total = data.news_list.total;
          extractedData.perPage = data.news_list.per_page;
          return extractedData;
        }
      }
      return data;
    });

    return {
      getList: function (args) {
        return News.getList(args);
      },
      updateNews: function (newsItem) {
        return newsItem.save();
      },
      createNews: function (newsItem) {
        return News.post({
          subject: newsItem.subject,
          body: newsItem.body
        });
      },
      publishNews: function (newsId, publish) {
        return Restangular.one('news', newsId).post('', {
          news_id: newsId,
          publish: publish
        });
      },
      deleteNews: function (newsId) {
        return Restangular.one('news', newsId).remove({news_id: newsId});
      }
    };
  });
