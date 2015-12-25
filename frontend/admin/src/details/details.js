const dependencies = [
  require('../../../shared/appGlobalState/appGlobalState').default.name
];

export default angular.module('boss.admin.details', dependencies)
  .controller('DetailsBaseCtrl', function ($rootScope, $scope, $state, appGlobalState) {
    $scope.customDetailsHeader = {tpl: null};

    var cancelListener = $rootScope.$on('$stateChangeSuccess', function (e, toState) {
      var toStatesLength = (toState.name.match(/\./g) || []).length + 1,
          thisStatesLength = ($scope.thisState.match(/\./g) || []).length + 1;
      if (toState.name === $scope.thisState) {
        $state.go(appGlobalState.lastVisitDetails[$scope.thisState] || $scope.defaultState);
      } else if (toState.name !== $scope.thisState && _.startsWith(toState.name, $scope.thisState)) {
        if (toStatesLength - thisStatesLength > 1) {
          if (toState.name.substring(0, toState.name.lastIndexOf('.'))) {
            appGlobalState.lastVisitDetails[$scope.thisState] = toState.name.substring(0, toState.name.lastIndexOf('.'));
          } else {
            appGlobalState.lastVisitDetails[$scope.thisState] = toState.name;
          }
        } else {
          appGlobalState.lastVisitDetails[$scope.thisState] = toState.name;
        }
      } else if (toState.name !== $scope.thisState && !_.startsWith(toState.name, $scope.thisState)) {
        delete appGlobalState.lastVisitDetails[$scope.thisState];
        appGlobalState.detailsWide = angular.isDefined(toState.data.detailsWide) ? toState.data.detailsWide : false;
      }
    });
    if ($state.is($scope.thisState)) {
      $state.go(appGlobalState.lastVisitDetails[$scope.thisState] || $scope.defaultState);
    }
    $scope.$on('$destroy', function () {
      cancelListener();
    });
    $scope.globalState = appGlobalState;
    $scope.stateIs = function (stateName) {
      return ($state.current.name === stateName);
    };
    $scope.toggleWide = function () {
      appGlobalState.detailsWide = !appGlobalState.detailsWide;
    };
  });
