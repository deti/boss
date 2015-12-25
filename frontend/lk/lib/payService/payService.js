const dependencies = [
  require('../../../shared/asynchronousLoader/asynchronousLoader').default.name
];

export default angular.module('boss.payService', dependencies)
  .factory('payService', function (asynchronousLoader, $q, CONST, Restangular) {
    function pay(amount, customer, data = {}) {
      var deferred = $q.defer();
      var options = {
        publicId: CONST.local.payments.cloudpayments.public_id,
        description: 'Replenishment of the account', //purpose
        amount: amount,
        currency: customer.currency,
        accountId: `${customer.customer_id}`,
        email: customer.email,
        data: data
      };

      var widget = new cp.CloudPayments();
      widget.charge(options,
        function (options) { // success
          console.log(arguments);
          deferred.resolve(options);
        },
        function (reason, options) { // fail
          deferred.reject({
            reason,
            options
          });
        });

      return deferred.promise;
    }

    return {
      load: function () {
        return asynchronousLoader.load('https://widget.cloudpayments.ru/bundles/cloudpayments');
      },
      payOnce: function (amount, customer, saveAsDefault = false) {
        return pay(amount, customer, {saveAsDefault});
      },
      payFromCard: function (amount, cardId) {
        console.log(cardId);
        return Restangular.one('customer').one('me').one('payments').one('withdraw').customPOST({
          amount: amount.toFixed(2),
          card_id: cardId
        });
      },
      payRecurrent: function (amount, customer, interval = 'Month', period = 1) {
        var data = {
          cloudPayments: {
            recurrent: {interval, period}
          }
        };
        return pay(amount, customer, data);
      },
      cardsList: function () {
        return Restangular.one('customer').one('payments').one('cloudpayments').one('card').get()
          .then(function (rsp) {
            return rsp.cards;
          });
      },
      removeCard: function (cardId) {
        return Restangular.one('customer').one('payments').one('cloudpayments').one('card').customDELETE('', {
          card_id: cardId
        });
      }
    };
  });
