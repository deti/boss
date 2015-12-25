const dependencies = [
  require('./RestorePasswordCtrl').default.name
];

export default angular.module('boss.lk.restorePassword', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('restorePassword', {
        parent: 'boss-clean',
        url: '/restore',
        views: {
          'main@boss-clean': {
            controller: 'RestorePasswordCtrl',
            template: require('./restorePassword.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-auth',
          pageTitle: 'Password recovery'
        },
        resolve: {
          captcha: function (asynchronousLoader, appLocale) {
            return appLocale.getLang()
              .then(function (lang) {
                return asynchronousLoader.load(`https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit&hl=${lang}`);
              });
          }
        }
      })
      .state('restorePasswordComplete', {
        parent: 'boss-clean',
        url: '/restore-complete',
        views: {
          'main@boss-clean': {
            template: require('./restorePasswordComplete.tpl.html')
          }
        },
        data: {
          bodyClassname: 'body-auth'
        }
      });
  });
