const dependencies = [
  require('../../lib/userService/userService').default.name,
  require('../../../shared/popupErrorService/popupErrorService').default.name,
  require('../../../shared/dialog/dialog').default.name,
  require('../../lib/addressService/addressService').default.name,
  require('../../lib/payService/payService').default.name
];

const entityTplPath = require('./settings.entity.partial.tpl.html');
const privateTplPath = require('./settings.private.partial.tpl.html');
const withdrawTplPath = require('./settings.withdraw.partial.tpl.html');

export default angular.module('boss.lk.SettingsCtrl', dependencies)
  .controller('SettingsCtrl', function SettingsCtrl($scope, $filter, toaster, userService, popupErrorService, dialog,
                                                    addressService, payService, countries, subscriptions, userInfo,
                                                    subscriptionsInfo, locales, withdrawPeriods,
                                                    cardsList, withdrawParams) {
    $scope.cardList = _.sortBy(cardsList, 'status');
    $scope.countries = countries;
    $scope.locales = locales;
    $scope.periods = withdrawPeriods;
    $scope.user = _.cloneDeep(userInfo);
    $scope.subscriptions = subscriptions;
    $scope.subscriptionsInfo = subscriptionsInfo;
    $scope.pass = {};
    $scope.withdrawParams = withdrawParams;

    $scope.user.withdraw_period_name = _.result(_.find($scope.periods, 'period_id', $scope.user.withdraw_period), 'localized_name');
    $scope.user.withdraw_period_name = $filter('localizedName')($scope.user, 'withdraw_period_name');

    $scope.user.sameAddress = addressService.isTheSame($scope.user);

    $scope.$watch('user.sameAddress', function (newVal, oldVal) {
      if ($scope.type && newVal !== oldVal) {
        if (newVal) {
          addressService.set($scope.user, true);
        }
      }
    });

    $scope.removeCard = function removeCard(card) {
      dialog.confirm($filter('translate')('Do you really want to remove card {{card_type}} **** **** {{last_four}}?', card))
        .then(function () {
          return payService.removeCard(card.card_id);
        })
        .then(function () {
          toaster.pop('success', $filter('translate')('Bound card was successfully deleted'));
          _.remove(cardsList, item => item.card_id === card.card_id);
          $scope.cardList = cardsList;
        });
    };

    $scope.selectLocale = function (localeCode) {
      return $scope.user.locale.toUpperCase() === localeCode.toUpperCase();
    };

    $scope.changePass = function () {
      userService.updatePassword($scope.pass.oldPassword, $scope.pass.newPassword)
        .then(function () {
          $scope.PasswordForm.$setPristine();
          $scope.pass = {};
        });
    };
    $scope.updateSubscriptions = function (form) {
      userService.updateSubscriptions($scope.subscriptions)
        .then(function () {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Subscriptions are updated'));
          form.$setUntouched();
        }, function (err) {
          form.$resetSubmittingState();
          popupErrorService.show(err);
        });
    };
    $scope.updateInfo = function (form) {
      if ($scope.user.sameAddress) {
        addressService.set($scope.user, true);
      }
      userService.update($scope.user)
        .then(function (updatedUserInfo) {
          form.$resetSubmittingState();
          angular.copy(updatedUserInfo.detailed_info, $scope.detailed_info);
          angular.copy(updatedUserInfo.detailed_info, userInfo.detailed_info);
          $scope.user.sameAddress = addressService.isTheSame($scope.user);
          toaster.pop('success', $filter('translate')('Info is updated'));
          $scope.ContactsForm.$setPristine();
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.updateLocale = function (form) {
      userService.setLocale($scope.user.locale)
        .then(function (rsp) {
          form.$resetSubmittingState();
          userInfo.locale = rsp.customer_info.locale;
          $scope.user.locale = rsp.customer_info.locale;
          toaster.pop('success', $filter('translate')('Info is updated'));
          $scope.AccountForm.$setPristine();
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.resendConfirmationEmail = function () {
      userService.sendConfirmEmail(null) // we do not have confirm_token on this page
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Email is sent!'));
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.restoreOSPassword = function () {
      userService.restoreOSPassword()
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('A letter with Openstack password has been sent to you'));
        }, function (err) {
          popupErrorService.show(err);
        });
    };

    $scope.updateAutoWithdraw = function (form) {
      userService.setAutoWithdraw($scope.withdrawParams)
        .then(function () {
          form.$resetSubmittingState();
          toaster.pop('success', $filter('translate')('Info is updated'));
        })
        .catch(function (rsp) {
          form.$parseErrors(rsp);
        });
    };

    $scope.entityTplPath = entityTplPath;
    $scope.privateTplPath = privateTplPath;
    $scope.withdrawTplPath = withdrawTplPath;
  });
