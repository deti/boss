const dependencies = [
  require('../../../shared/openstackService/Keystone').default.name
];

export default angular.module('boss.admin.osLogin', dependencies)
  .config(function config($stateProvider) {
    $stateProvider
      .state('osLogin', {
        parent: 'boss',
        url: '/osLogin',
        views: {
          'main@boss': {
            controller: 'OSLoginCtrl as OSLoginCtrl',
            template: require('./osLogin.tpl.html')
          }
        },
        data: {
          pageTitle: 'OSLogin'
        }
      });
  })
  .controller('OSLoginCtrl', function OSLoginCtrl(Keystone, $state) {
    if (Keystone.authPair) {
      $state.go('projects');
    }
    this.login = '';
    this.password = '';
    this.submit = form => {
      Keystone.authenticate(this.login, this.password)
        .then(t => {
          form.$resetSubmittingState();
          $state.go('projects');
        })
        .catch(e => form.$parseErrors(e));
    };
  });
