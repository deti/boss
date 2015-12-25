const dependencies = [
  'toaster',
  require('../../../lib/newsService/newsService').default.name
];

export default angular.module('boss.admin.NewsNewCtrl', dependencies)
  .controller('NewsNewCtrl', function ($scope, $state, newsService, $filter, toaster) {
    $scope.newsItem = {};
    $scope.create = function (form) {
      newsService.createNews($scope.newsItem)
        .then(function () {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('News is successfully created'));
          $state.go('news', {}, {reload: true});
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };
  });
