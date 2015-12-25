const dependencies = ['mgcrea.ngStrap.tooltip'];

export default angular.module('boss.copyToClipboard', dependencies)
  .directive('bsCopyToClipboard', function ($compile, $tooltip, $timeout, $filter) {
    return {
      restrict: 'A',
      terminal: true,
      priority: 1000,
      link: function (scope, element) {
        element.attr('clip-copy', element.attr('bs-copy-to-clipboard'));
        element.attr('ng-click', 'showCopySuccess($event)');
        element.removeAttr('bs-copy-to-clipboard');
        element.removeAttr('copy-message');

        var tooltip;
        scope.showCopySuccess = function ($event) {
          if (!tooltip) {
            tooltip = $tooltip(angular.element($event.target), {
              title: $filter('translate')('Copied'),
              trigger: 'manual',
              placement: 'bottom'
            });
            tooltip.$promise.then(function () {
              tooltip.show();
              $timeout(tooltip.hide, 3000);
            });
          } else {
            tooltip.show();
            $timeout(tooltip.hide, 3000);
          }
        };
        $compile(element)(scope);
      }
    };
  });
