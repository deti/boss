const dependencies = [];

export default angular.module('boss.admin.NewsCtrl', dependencies)
  .controller('NewsCtrl', function NewsCtrl($scope, $filter, newsData) {
    $scope.pages = Math.ceil(parseInt(newsData.total) / parseInt(newsData.perPage));
    $scope.news = newsData.map(item => {
      item.published = item.published ? $filter('date')(item.published, 'short') : 'No';
      return item;
    });
    $scope.columns = [
      {field: 'subject', title: $filter('translate')('Title')},
      {field: 'body', title: $filter('translate')('News')},
      {field: 'published', title: $filter('translate')('Published')}
    ];
    $scope.searchTags = [];
    $scope.filters = [];
  });
