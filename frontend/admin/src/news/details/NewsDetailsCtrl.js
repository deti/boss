import '../../../lib/newsService/newsService';
import '../../../../shared/popupErrorService/popupErrorService';

export default angular.module('boss.admin.NewsDetailsCtrl', ['restangular', 'toaster', 'ui.router', 'boss.newsService', 'boss.popupErrorService'])
  .controller('NewsDetailsCtrl', function NewsDetailsCtrl($scope, $state, newsItem, newsService, Restangular, $filter, toaster, popupErrorService) {
    $scope.newsItem = Restangular.copy(newsItem);

    $scope.update = function () {
      newsService.updateNews($scope.newsItem)
        .then(function () {
          Restangular.sync($scope.newsItem, newsItem);
          toaster.pop('success', $filter('translate')('News is successfully updated'));
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.publish = function (published) {
      newsService.publishNews(parseInt($scope.newsItem.news_id), !published)
        .then(function () {
          toaster.pop('success', $filter('translate')('Publication parameter is changed'));
          $state.go('news', {}, {reload: true});
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.delete = function () {
      newsService.deleteNews(parseInt($scope.newsItem.news_id))
        .then(function () {
          toaster.pop('success', $filter('translate')('News is deleted'));
          $state.go('news', {}, {reload: true});
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };
  });
