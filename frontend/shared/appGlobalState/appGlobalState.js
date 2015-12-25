const dependencies = [];

export default angular.module('boss.appGlobalState', dependencies)
  .value('appGlobalState', {
    detailsVisible: false,
    detailsWide: false,
    menuWide: false,
    lastVisitDetails: {}
  });
