const dependencies = [
  require('../../../shared/appLocale/appLocale').default.name
];

export default angular.module('boss.admin.header', dependencies)
  .controller('HeaderCtrl', function ($scope, userInfo, appLocale, langList) {
    $scope.langs = langList;
    $scope.userInfo = userInfo;
    $scope.currentLang = appLocale.getLang(true);
    $scope.setLang = appLocale.setLang;
    $scope.langShortNames = {
      en: 'ENG',
      ru: 'RUS'
    };
  });
