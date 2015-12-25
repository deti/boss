const dependencies = [
  'ui.bootstrap.modal', 'pascalprecht.translate',
  require('../bsCompileTemplate/bsCompileTemplate').default.name
];

export default angular.module('boss.dialog', dependencies)
  .factory('dialog', function ($modal, $filter) {
    return {
      confirm: function confirmDialog(header, buttonYesText = $filter('translate')('Yes'), buttonNoText = $filter('translate')('Cancel'), customTemplate = false, templateData = {}) {
        return $modal.open({
          template: require('./dialog.confirm.tpl.html'),
          controller: function ($scope) {
            $scope.header = header;
            $scope.templateData = templateData;
            $scope.customTemplate = customTemplate;
            $scope.buttonYesText = buttonYesText;
            $scope.buttonNoText = buttonNoText;
          }
        }).result;
      },
      alert: function alertDialog(header, buttonText = $filter('translate')('Ok')) {
        return $modal.open({
          template: require('./dialog.confirm.tpl.html'),
          controller: function ($scope) {
            $scope.header = header;
            $scope.buttonText = buttonText;
          }
        }).result;
      }
    };
  });
