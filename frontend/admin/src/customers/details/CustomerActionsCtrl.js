const dependencies = [
  'restangular',
  'toaster',
  'ui.bootstrap.modal',
  require('../../../lib/customerService/customerService').default.name,
  require('../../../../shared/popupErrorService/popupErrorService').default.name
];

const dialogTplPath = require('./dialog.block.partial.tpl.html');

export default angular.module('boss.admin.CustomerActionsCtrl', dependencies)
  .controller('CustomerActionsCtrl', function CustomerActionsCtrl($scope, $filter, $modal, toaster, Restangular, customerService, popupErrorService, customer) {
    $scope.customer = Restangular.copy(customer);

    $scope.makeProd = function () {
      customerService.makeProd(customer)
        .then(function (updatedCustomer) {
          Restangular.sync(updatedCustomer, $scope.customer);
          Restangular.sync(updatedCustomer, customer);
          toaster.pop('success', $filter('translate')('User account is successfully changed'));
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };
    $scope.toggleBlock = function () {
      var isBlocked = $scope.customer.blocked;
      $modal.open({
        templateUrl: dialogTplPath,
        controller: function ($scope) {
          $scope.block = isBlocked;
        }
      }).result.then(function (message) {
        customerService.setBlocked(customer, !customer.blocked, message)
          .then(function () {
            $scope.customer.blocked = !$scope.customer.blocked;
            Restangular.sync($scope.customer, customer);
            toaster.pop('success', $filter('translate')('User account is successfully changed'));
          })
          .catch(function (err) {
            popupErrorService.show(err);
          });
      });
    };

    $scope.toggleArchive = function () {
      customerService.archive($scope.customer)
        .then(function () {
          Restangular.sync($scope.customer, customer);
          toaster.pop('success', $filter('translate')('User account is successfully archived'));
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.recreateCloud = function () {
      customerService.recreateCloud($scope.customer)
        .then(function () {
          toaster.pop('success', $filter('translate')('Cloud is successfuly created'));
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.resetPassword = function () {
      customerService.resetPassword(customer)
        .then(function () {
          toaster.pop('success', $filter('translate')('User password is reset'));
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.resendConfirmationEmail = function () {
      customerService.sendConfirmEmail($scope.customer.customer_id)
        .then(function () {
          toaster.pop('success', $filter('translate')('Message is sent!'));
        })
        .catch(function (err) {
          popupErrorService.show(err);
        });
    };
  });
