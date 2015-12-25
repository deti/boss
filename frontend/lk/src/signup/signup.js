const dependencies = [
  require('./SignupCtrl').default.name,
  require('../../../shared/asynchronousLoader/asynchronousLoader').default.name,
  require('../../../shared/appLocale/appLocale').default.name,
  require('../../lib/bsStrongPasswordValidator/bsStrongPasswordValidator').default.name
];

export default angular.module('boss.lk.signup', dependencies)
  .config(function ($stateProvider) {
    $stateProvider.state('signup', {
      parent: 'authorization',
      url: '/signup?promo',
      views: {
        'form@authorization': {
          controller: 'SignupCtrl',
          template: require('./signup.tpl.html')
        }
      },
      data: {
        pageTitle: 'Registration'
      },
      resolve: {
        captcha: function (asynchronousLoader, appLocale) {
          return appLocale.getLang()
            .then(function (lang) {
              return asynchronousLoader.load(`https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit&hl=${lang}`);
            });
        }
      }
    });
  });
