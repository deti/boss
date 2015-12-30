const dependencies = [
  require('./Column').default.name
];

const templates = {
  normal: require('./templates/grid.tpl.html'),
  static: require('./templates/grid.static.tpl.html'),
  link: require('./templates/grid.link.tpl.html')
};

export default angular.module('boss.grid.BsGridCtrl', dependencies)
  .controller('BsGridCtrl', function BsGridCtrl($scope, $attrs, $element, $rootScope, $timeout, $state, Column) {
    var config = $scope.$eval($attrs.config);
    this.$element = $element;
    this.gridId = _.uniqueId('bsGrid_');
    this.data = config.data;
    this.columns = config.columns.map(i => i instanceof Column ? i : new Column(i));

    if (config.uniqueField) {
      this.uniqueField = config.uniqueField;
    } else {
      console.warn('You should provide config.uniqueField');
      this.data.forEach(i => {
        i.__id = _.uniqueId();
      });
      this.uniqueField = '__id';
    }
    // sorting
    this.sortPredicate = false;
    this.sortReverse = false;
    this.applySorting = (column) => {
      if (this.sortPredicate !== column.sortField) { // column have not sorted yet
        this.sortPredicate = column.sortField;
        this.sortReverse = !!column.reverse;
        column.sortClass = 'grid-sort-asc';
      } else if (this.sortReverse === !!column.reverse) { // column was sorted once
        this.sortReverse = !this.sortReverse;
        column.sortClass = 'grid-sort-desc';
      } else { // column was sorted twice, reset sorting
        this.sortReverse = false;
        this.sortPredicate = false;
        column.sortClass = '';
      }
    };

    var defaultSortColumn = _.find(this.columns, i => i.sortDefault);
    if (defaultSortColumn) {
      this.applySorting(defaultSortColumn);
    }

    // links
    if ($attrs.type === 'link') {
      const linkDefaults = {
        sref: '',
        idField: this.uniqueField,
        srefPushToLocation: false
      };
      this.link = _.assign({}, linkDefaults, config.link);
    }

    // update scrollbar size on state change
    var updateScrollbar = () => {
      $timeout(() => this.scrollBarRefresh = $state.current.name);
    };
    var cancelListener = $rootScope.$on('$stateChangeSuccess', updateScrollbar);
    $scope.$on('$destroy', cancelListener);
    updateScrollbar();

    // template initialization
    this.innerTpl = $attrs.type ? templates[$attrs.type] : templates.normal;
    this.filter = false;
    $scope.$watch('filter', val => this.filter = val);
  });
