const dependencies = [];

export default angular.module('boss.tableFilterTags', dependencies)
  .directive('bsTableFilterTags', function ($state, $stateParams) {
    return {
      restrict: 'E',
      template: require('./bsTableFilterTags.tpl.html'),
      scope: {
        searchTags: '='
      },
      link: function (scope, elem, attrs) {
        scope.stateName = attrs.stateName;

        scope.removeTag = function (tag) {
          if (tag.property && tag.property === 'ClearAll') {
            scope.searchTags.forEach(tag => {
              if (tag.property) {
                $stateParams[tag.property] = undefined;
              }
            });
            $stateParams.text = undefined;
          } else {
            if (tag.property) {
              $stateParams[tag.property] = undefined;
            } else if (tag.text) {
              if (_.isArray($stateParams.text)) {
                _.remove($stateParams.text, value => {
                  return value === tag.text;
                });
              } else {
                $stateParams.text = undefined;
              }
            }
          }
          $stateParams.page = undefined;
          $stateParams.filterActive = false;
          $state.go($state.$current.name, $stateParams);
        };
      }
    };
  });
