const dependencies = [];

export default angular.module('boss.popupDetails', dependencies)
  .directive('bsPopupDetails', function ($document) {
    return {
      restrict: 'E',
      scope: {
        structure: '='
      },
      template: require('./bsPopupDetails.tpl.html'),
      link: function (scope, elem, attr) {
        scope.showPopup = false;

        scope.togglePopup = function () {
          scope.showPopup = !scope.showPopup;
        };

        var eventcb = function (event) {
          if (elem.find(event.target).length > 0) {
            return;
          }
          scope.showPopup = false;
          scope.$apply();
        };

        $document.on('click', eventcb);

        scope.$on('$destroy', function () {
          $document.off('click', eventcb);
        });
      }
    };
  });
