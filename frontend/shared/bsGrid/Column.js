const dependencies = [];

export default angular.module('boss.grid.Column', dependencies)
  .factory('Column', function (appLocale) {
    const defaults = {
      reverse: false,
      cellClass: '',
      filter: false,
      sortField: ''
    };
    class Column {
      id = _.uniqueId('grid-column-');

      constructor(config) {
        _.assign(this, defaults, config);
        this.type = getCellType(this);
        this.sortField = this.getSortField();
      }

      getSortField() {
        if (this.sortField) {
          return _.isFunction(this.sortField) ? this.sortField() : this.sortField;
        }
        if (this.filter) {
          var localizedField = getLocalizedField(this.filter);
          if (localizedField) {
            var lang = appLocale.getLang(true);
            if (this.field) {
              return `${this.field}.${localizedField}.${lang}`;
            }
            return `${localizedField}.${lang}`;
          }
        }
        return this.field;
      }
    }

    function getCellType(c) {
      if (c.value && !c.template) {
        return 'value';
      }
      if (c.template && !c.value) {
        return 'template'
      }
      if (c.field && !c.value && !c.template) {
        return 'field';
      }
      if (!c.field && !c.value && !c.template) {
        return 'noField';
      }
    }

    function getLocalizedField(filter) {
      if (_.isArray(filter)) {
        filter = _.find(filter, (item) => {
          return item === 'localizedName' || _.isObject(item) && item.name === 'localizedName';
        });
        if (filter === undefined) {
          return false;
        }
      }
      if (filter === 'localizedName') {
        return 'localized_name';
      }
      if (_.isObject(filter) && filter.name === 'localizedName') {
        return filter.args ? filter.args[0] : 'localized_name';
      }
      return false;
    }

    return Column;
  });
