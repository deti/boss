const dependencies = ['toaster', 'pascalprecht.translate'];
export default angular.module('boss.popupErrorService', dependencies)
  .factory('popupErrorService', function (toaster, $filter) {
    return {
      show: function (errorObj) {
        if (errorObj.localized_message) {
          toaster.pop('error', errorObj.localized_message);
        } else if (errorObj.data && errorObj.data.localized_message) {
          toaster.pop('error', errorObj.data.localized_message);
        } else {
          toaster.pop('error', $filter('translate')('Server error'));
        }
      }
    };
  });
