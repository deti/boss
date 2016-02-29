const dependencies = ['mgcrea.ngStrap.tooltip'];

export default angular.module('boss.copyToClipboard', dependencies)
  .directive('bsCopyToClipboard', function ($compile, $tooltip, $timeout, $filter) {
    return {
      restrict: 'A',
      terminal: true,
      priority: 1000,
      link: function (scope, element) {
        element.attr('clip-copy', element.attr('bs-copy-to-clipboard'));
        element.attr('clip-click-fallback', `noFlashFallback(${element.attr('bs-copy-to-clipboard')})`);
        element.attr('clip-click', 'showCopySuccess()');

        element.removeAttr('bs-copy-to-clipboard');
        element.removeAttr('copy-message');

        var tooltip;
        scope.showCopySuccess = function () {
          if (!tooltip) {
            tooltip = $tooltip(element, {
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
        scope.noFlashFallback = function (copy) {
          window.prompt($filter('translate')('Press ctrl+c to copy the text below.'), copy);
        };
        $compile(element)(scope);
      }
    };
  });
