const dependencies = [
  require('../popupErrorService/popupErrorService').default.name
];
// fill-in form errors based on http status code and server responses
export default angular.module('boss.serverValidate', dependencies)
  .directive('bsServerValidate', function ($parse, popupErrorService) {
    return {
      require: 'form',
      link: function (scope, element, attrs, formController) {
        var httpCode2Error = angular.extend({500: 'ServerError'}, $parse(attrs.bsServerValidate)(scope)),
          serverErrors = [],
          alreadyBound = false;

        /**
         * Removes errors from server on form fields changes
         */
        var clearServerErrors = function () {
          Object.keys(httpCode2Error).forEach(key => {
            formController.$setValidity(httpCode2Error[key], true);
          });
          formController.$setValidity('unclassified', true);
          serverErrors.forEach(key => {
            formController[key].$setValidity('server', true);
          });
          serverErrors = [];
        };

        function getMessage(string) {
          if (!string) {
            return {
              key: '',
              text: ''
            };
          }
          var message = string.split(' '),
            key = message.shift(),
            text = message.join(' ');
          return {
            key: key,
            text: text
          };
        }

        formController.$parseErrors = function (rsp) {
          if (formController.$resetSubmittingState) {
            formController.$resetSubmittingState();
          }
          var split, field, localizedMessage, message;

          if (!alreadyBound) {
            for (var key in formController) {
              if (formController.hasOwnProperty(key) && String(key).charAt(0) !== '$' && angular.isObject(formController[key]) && formController[key].$$parentForm === undefined) {
                formController[key].$viewChangeListeners.unshift(clearServerErrors);
                formController[key].$parsers.unshift((value) => { // use $parsers for 'hard' cases like ngTagsInput
                  clearServerErrors();
                  return value;
                });
              }
            }
            alreadyBound = !alreadyBound;
          }

          if (typeof rsp.data.field !== 'undefined') {
            split = rsp.data.field.split('.');
            field = (split.length > 1) ? _.last(split) : rsp.data.field;

            if (formController[field]) {
              formController[field].$setValidity('server', false);
              formController[field].$server_error = rsp.data.localized_message;
              serverErrors.push(field);
            } else {
              popupErrorService.show(rsp);
            }
            return;
          }

          localizedMessage = getMessage(rsp.data.localized_message);
          message = getMessage(rsp.data.message);
          if (!message.key || localizedMessage.key !== message.key) {
            // error without field
            if (rsp.status in httpCode2Error) {
              formController.$setValidity(httpCode2Error[rsp.status], false);
              formController['$server_error_' + httpCode2Error[rsp.status]] = rsp.data.localized_message;
            } else {
              formController.$setValidity('unclassified', false);
              formController.$server_unclassified = rsp.data.localized_message;
            }
          } else {
            if (formController[localizedMessage.key]) {
              formController[localizedMessage.key].$setValidity('server', false);
              formController[localizedMessage.key].$server_error = localizedMessage.text;
              serverErrors.push(localizedMessage.key);
            } else {
              popupErrorService.show(rsp);
            }
          }
        };

        element.bind('submit', function () {
          if (formController.$invalid) {
            return false;
          }
        });
      }
    };
  });
