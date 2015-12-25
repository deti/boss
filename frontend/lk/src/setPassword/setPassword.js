const dependencies = [
  require('./SetPasswordCtrl').default.name,
  require('../../lib/bsStrongPasswordValidator/bsStrongPasswordValidator').default.name,
  require('../../../shared/bsMatch/bsMatch').default.name
];

export default angular.module('boss.lk.setPassword', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('setPassword', {
        parent: 'boss-clean',
        url: '/set-password/:key',
        views: {
          'main@boss-clean': {
            controller: 'SetPasswordCtrl',
            template: require('./setPassword.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-auth',
          pageTitle: 'Password recovery'
        },
        resolve: {
          isValid: function (userService, $stateParams) {
            return userService.resetPasswordIsValid($stateParams.key);
          }
        }
      });
  });
