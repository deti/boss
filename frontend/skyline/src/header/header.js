const dependencies = [
  require('../../../shared/appLocale/appLocale').default.name
];

export default angular.module('skyline.HeaderCtrl', dependencies)
  .controller('HeaderCtrl', function ($scope, appLocale, $window, $document) {
    $scope.langs = {
      ru: {
        ru: 'русский',
        en: 'russian'
      },
      en: {
        ru: 'английский',
        en: 'english'
      }
    };
    $scope.newsList = [];

    $scope.currentLang = appLocale.getLang(true);
    $scope.setLang = appLocale.setLang;
    $scope.langShortNames = {
      en: 'ENG',
      ru: 'RUS'
    };
    // close dropdown menu when click inside iframe
    $scope.isOpen = [];
    $window.addEventListener('blur', function () {
      if ($document[0].activeElement && $document[0].activeElement.tagName.toLowerCase() === 'iframe') {
        $scope.isOpen = $scope.isOpen.map(item => false);
        $scope.$apply();
      }
    });
  });
