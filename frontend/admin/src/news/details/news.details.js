import './NewsDetailsCtrl';

const detailsEmptyTpl = require('../../details/details.empty.tpl.html');
const detailsTpl = require('./news.details.tpl.html');

export default angular.module('boss.admin.news.details', ['boss.admin.NewsDetailsCtrl'])
  .config(function ($stateProvider) {
    $stateProvider
      .state('news.details', {
        url: '/{id:[0-9]*}',
        views: {
          'details@boss': {
            template: function ($stateParams) {
              return $stateParams.isEmpty ? detailsEmptyTpl : detailsTpl;
            },
            controllerProvider: function ($stateParams) {
              if ($stateParams.isEmpty) {
                return function () {
                };
              } else {
                return 'NewsDetailsCtrl';
              }
            }
          }
        },
        data: {
          detailsVisible: true
        },
        resolve: {
          newsItem: function (newsData, $stateParams) {
            return _.findWhere(newsData, {news_id: parseInt($stateParams.id)});
          }
        }
      });
  });
