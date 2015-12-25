const dependencies = [
  require('./StatisticsCtrl').default.name
];

export default angular.module('boss.lk.statistics', dependencies)
  .config(function ($stateProvider) {
    $stateProvider
      .state('statistics', {
        parent: 'boss',
        url: '/statistics?after?before',
        views: {
          'main@boss': {
            controller: 'StatisticsCtrl',
            template: require('./statistics.tpl.html')
          }
        },
        data: {
          pageTitle: 'Statistics'
        }
      });
  });
