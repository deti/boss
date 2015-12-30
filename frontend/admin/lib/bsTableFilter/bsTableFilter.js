const dependencies = [
  'angular-click-outside',
  'smart-table',
  'ui.router',
  'ngTagsInput',
  'pascalprecht.translate'
];

export default angular.module('boss.tableFilter', dependencies)
  .directive('bsTableFilter', function ($state, $stateParams, $filter, $timeout) {
    var filter = $filter('filter');
    function getSearchExpression(props) {
      return function (item) {
        var res;
        for (var i = 0; i < props.length; i++) {
          res = filter([item], {$: props[i].replace(/-/g, ' ')});
          if (res.length === 0) {
            break;
          }
        }
        return res.length !== 0;
      };
    }

    function addClearAllTag (searchTags) {
      if (searchTags.length >= 3) {
        searchTags.push({
          text: $filter('translate')('Clear All'),
          property: 'ClearAll'
        });
      }
    }

    function getSearchTags(params, filters) {
      var searchTags = [];
      Object.keys(params).forEach(paramName => {
        var filter = _.find(filters, filter => filter.property === paramName);
        if (filter === undefined) {
          return;
        }
        var option = _.find(filter.options, opt => opt.val == params[paramName]);
        if (option === undefined) {
          return;
        }
        searchTags.push({
          text: option.text,
          property: paramName,
          val: option.val
        });
      });
      function addTextSearch(item) {
        searchTags.push({text: item.replace(/-/g, ' ')});
      }
      if (params.text) {
        if (_.isArray(params.text)) {
          params.text.forEach(addTextSearch);
        } else {
          addTextSearch(params.text);
        }
      }

      return searchTags;
    }

    return {
      restrict: 'E',
      template: require('./bsTableFilter.tpl.html'),
      require: ['?^stTable', '?^bsGridExpose'],
      scope: {
        searchTags: '=',
        filters: '='
      },
      link: function (scope, element, attrs, [stTableCtrl, gridCtrl]) {
        scope.searchActive = ($stateParams.page === undefined) ? !!$stateParams.filterActive : false;
        scope.stateName = attrs.stateName;
        scope.searchTags = getSearchTags($stateParams, scope.filters);
        addClearAllTag(scope.searchTags);
        if ($stateParams.text) {
          var searchExpression;
          if (_.isArray($stateParams.text)) {
            searchExpression = getSearchExpression($stateParams.text);
          } else {
            searchExpression = getSearchExpression([$stateParams.text]);
          }
          if (stTableCtrl) {
            stTableCtrl.tableState().search.predicateObject = searchExpression;
            stTableCtrl.pipe();
          } else if (gridCtrl) {
            gridCtrl.filters = searchExpression;
          }
        }

        if (scope.searchActive) {
          $timeout(function () {
            element.find('.input').focus();
          });
        }
      },
      controller: function ($scope, $document, $timeout) {
        $scope.hideSearch = function () {
          $scope.searchActive = false;
        };

        function keydownListener (e) {
          if (!$scope.searchActive) {
            return;
          }
          if (e.keyCode === 13) {
            $timeout($scope.hideSearch);
            e.preventDefault();
            e.stopPropagation();
          }
        }

        $scope.toggleSearch = function () {
          $scope.searchActive = !$scope.searchActive;
        };
        $document.on('keydown', keydownListener);

        $scope.addSearchTag = function (option, property) {
          var index = _.findIndex($scope.searchTags, item => {
            return item.property === property;
          });
          if (index !== -1 && $scope.searchTags[index].val === option.val) {
            // this value already exists, remove it
            $scope.searchTags.splice(index, 1);
            $scope.search();
            return;
          }
          if (index !== -1) {
            $scope.searchTags.splice(index, 1);
          }
          var val = _.clone(option);
          val.property = property;
          $scope.searchTags.push(val);
          $scope.search();
        };

        $scope.tagAdded = function () {
          $scope.searchActive = false;
          $scope.search();
        };

        $scope.tagRemoved = function ($tag) {
          if ($tag.property == 'ClearAll') {
            $scope.searchTags = [];
          }
          $scope.search();
        };

        $scope.search = function () {
          var queue = {text: []};
          $scope.searchTags.forEach(tag => {
            if (tag.property === undefined) {
              queue.text.push(tag.text);
            } else {
              queue[tag.property] = tag.val;
            }
          });
          queue.page = undefined;
          queue.filterActive = $scope.searchActive;
          if ($stateParams.id) {
            queue.id = $stateParams.id;
          }
          $state.go($state.$current.name, queue, {
            inherit: false
          });
        };
      }
    };
  });
