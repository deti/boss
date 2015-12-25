const dependencies = [
  require('./SupportCtrl').default.name
];

export default angular.module('boss.lk.support', dependencies)
  .config(function config($stateProvider) {
    $stateProvider.state('support', {
      parent: 'boss',
      url: '/support',
      views: {
        'main@boss': {
          controller: 'SupportCtrl',
          template: require('./support.tpl.html')
        }
      },
      data: {
        pageTitle: 'Support'
      }
    });
  });
