const dependencies = [];

export default angular.module('boss.dropdownButton', dependencies)
  .directive('bsDropdownButton', function () {
    return {
      template: require('./bsDropdownButton.tpl.html'),
      restrict: 'E',
      scope: {
        action: '&',
        title: '@',
        options: '=',
        value: '='
      },
      link: function (scope) {
        if (!scope.value) {
          scope.value = Object.keys(scope.options)[0];
        }
      }
    };
  });
