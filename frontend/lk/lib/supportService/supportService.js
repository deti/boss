const dependencies = ['restangular'];

export default angular.module('boss.supportService', dependencies)
  .factory('supportService', function (Restangular) {
    return {
      sendMessage: function (message) {
        if (message.copies && message.copies.length) {
          message.copies = message.copies.map(copy => {
            return copy.text;
          });
        }
        return Restangular.one('customer').one('support').post('', {
          subject: message.subject,
          body: message.body,
          copy: message.copies
        });
      }
    };
  });
