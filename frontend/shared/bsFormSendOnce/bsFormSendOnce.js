const dependencies = [];

export default angular.module('boss.formSendOnce', dependencies)
  .directive('bsFormSendOnce', function ($timeout) {
    return {
      require: 'form',
      link: function (scope, element, attrs, formController) {
        const resetTimeout = parseInt(attrs.bsFormSendOnce) || 10 * 1000;
        const submitButton = element.find('button[type=submit]:first');

        formController.$resetSubmittingState = function () {
          formController.$$submiting = false;
          submitButton.attr('disabled', false);
          submitButton.removeClass('submitting');
        };

        element.bind('submit', function () {
          if (formController.$$submiting) {
            return false;
          }
          formController.$$submiting = true;
          submitButton.attr('disabled', true);
          submitButton.addClass('submitting');
          $timeout(formController.$resetSubmittingState, resetTimeout);
        });
      }
    };
  });
