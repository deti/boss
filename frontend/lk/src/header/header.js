const dependencies = [
  require('../../lib/newsService/newsService').default.name,
  require('../../../shared/appLocale/appLocale').default.name,
  require('../../../shared/localStorage/localStorage').default.name
];

export default angular.module('boss.lk.header', dependencies)
  .controller('HeaderCtrl', function ($scope, userInfo, appLocale, newsService, localStorage, langList, $window, $document) {
    $scope.langs = langList;
    $scope.updateLastSeenNews = function () {
      if ($scope.newsList[0]) {
        localStorage.setItem('lastNews', $scope.newsList[0].news_id);
        $scope.newNewsCount = 0;
      }
    };
    $scope.newsList = [];
    $scope.$watch('userInfo.email', function (val) {
      if (!val) {
        return;
      }
      newsService.getList().then(function (newsList) {
        $scope.newsList = _.sortBy(newsList, 'published').reverse();
        var lastNews = localStorage.getItem('lastNews', 0);
        $scope.newNewsCount = newsList.filter(item => item.news_id > lastNews).length;
      });
    });

    $scope.userInfo = userInfo;
    $scope.currentLang = appLocale.getLang(true);
    $scope.setLang = appLocale.setLang;
    $scope.langShortNames = {
      en: 'ENG',
      ru: 'RUS'
    };
    // close dropdown menu when click inside iframe
    $scope.isOpen = [];
    $window.addEventListener('blur', function () {
      if ($document[0].activeElement.tagName.toLowerCase() === 'iframe') {
        $scope.isOpen = $scope.isOpen.map(item => false);
        $scope.$apply();
      }
    });
  });
