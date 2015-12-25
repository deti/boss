const dependencies = [
  require('../../../shared/textPreview/textPreview').default.name
];

export default angular.module('boss.lk.NewsCtrl', dependencies)
  .controller('NewsCtrl', function NewsCtrl($scope, newsData, textPreview) {
    $scope.news = newsData.plain().map(item => {
      item.showFullBody = false;
      var preview = textPreview(item.body, 498);
      item.bodyPreview = preview.main;
      item.bodyRest = preview.rest;
      if (!preview.rest.length) {
        item.showFullBody = true;
      }
      return item;
    });
    $scope.news = _.sortBy($scope.news, 'published').reverse();
  });
