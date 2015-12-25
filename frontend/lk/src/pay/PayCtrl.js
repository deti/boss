const dependencies = [
  'angular-loading-bar',
  'toaster',
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../lib/payService/payService').default.name,
  require('../../lib/userService/userService').default.name
];

const invoiceTemplatePath = require('./pay.invoice.partial.tpl.html');
const cardsTemplatePath = require('./pay.cards.partial.tpl.html');

export default angular.module('boss.lk.PayCtrl', dependencies)
  .controller('PayCtrl', function PayCtrl($scope, $filter, cfpLoadingBar, toaster, payService, popupErrorService, userService, userInfo, payScript, cardsList) {
    $scope.invoiceTemplatePath = invoiceTemplatePath;
    $scope.cardsTemplatePath = cardsTemplatePath;
    $scope.cards = cardsList;
    $scope.userInfo = userInfo;

    $scope.cardFormData = {
      amount: 0,
      saveAsDefault: cardsList.length === 0,
      selectedCard: cardsList.length === 0 ? 'null' : _.find(cardsList, {status: 'active'}).card_id.toString()
    };

    $scope.invoiceFormData = {
      date: new Date(),
      amount: 0
    };

    $scope.acceptanceFormData = {};

    $scope.pay = function (form) {
      if ($scope.cardFormData.selectedCard !== 'null') {
        payService.payFromCard($scope.cardFormData.amount, $scope.cardFormData.selectedCard)
          .then(rsp => {
            return userService.userInfo(true);
          })
          .then(updatedUserInfo => {
            toaster.pop('success', $filter('translate')('The payment was successful'));
            angular.copy(updatedUserInfo, userInfo);
            $scope.cardFormData.saveAsDefault = false;
            $scope.cardFormData.amount = 0;
            form.$setPristine();
          })
          .catch(function (e) {
            popupErrorService.show(e);
          });
      } else {
        payService.payOnce($scope.cardFormData.amount, userInfo, $scope.cardFormData.saveAsDefault)
          .then(function (data) {
            return userService.userInfo(true);
          })
          .then(function (updatedUserInfo) {
            toaster.pop('success', $filter('translate')('The payment was successful'));
            angular.copy(updatedUserInfo, userInfo);
            $scope.cardFormData.saveAsDefault = false;
            $scope.cardFormData.amount = 0;
            form.$setPristine();
          })
          .catch(function (e) {
            toaster.pop('error', e.reason);
          });
      }
    };

    $scope.downloadInvoice = function (form) {
      userService.downloadInvoice($scope.invoiceFormData.amount, $scope.invoiceFormData.date)
        .then(function () {
          form.$resetSubmittingState();
        })
        .catch(function (e) {
          popupErrorService.show(e);
        });
    };

    $scope.downloadAcceptance = function () {
      cfpLoadingBar.start();
      userService.downloadReport($scope.acceptanceFormData.startDate, $scope.acceptanceFormData.endDate, 'pdf', 'acceptance_act')
        .then(function () {
          cfpLoadingBar.complete();
        })
        .catch(function (e) {
          popupErrorService.show(e);
          cfpLoadingBar.complete();
        });
    };
  });
