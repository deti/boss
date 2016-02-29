const dependencies = [
  require('../appLocale/appLocale').default.name
];

export default angular.module('boss.table.TableColumn', dependencies)
  .factory('TableColumn', function (appLocale) {
    function getLocalizedField(filter) {
      if (_.isArray(filter)) {
        filter = _.find(filter, item => {
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

    class TableColumn {
      constructor({title, width, titleClass, sortDefault, sortField, reverse, cellClassFn, cellClass, field, value, template, templateUrl, filter}) {
        this.id = _.uniqueId('column_');
        this.title = title;
        this.width = width;
        this.titleClass = titleClass;
        this.sortDefault = sortDefault;
        this.sortField = sortField;
        this.reverse = reverse;
        this.cellClassFn = cellClassFn;
        this.cellClass = cellClass || '';
        this.field = field;
        this.value = value;
        this.template = template;
        this.templateUrl = templateUrl;
        this.filter = filter;

        this.type = this.getCellType();
        this.usedSortField = this.getSortField();
      }
      getSortField() {
        var lang = appLocale.getLang(true);
        if (this.sortField) {
          return _.isFunction(this.sortField) ? this.sortField() : this.sortField;
        }
        if (this.filter) {
          var localizedField = getLocalizedField(this.filter);
          if (localizedField) {
            if (this.field) {
              return `${this.field}.${localizedField}.${lang}`;
            }
            return `${localizedField}.${lang}`;
          }
        }
        return this.field;
      }
      getCellType() {
        if (this.hasValue()) {
          return 'value';
        }
        if (this.hasTemplate()) {
          return 'template';
        }
        if (this.hasTemplateUrl()) {
          return 'templateUrl';
        }
        if (this.hasField()) {
          return 'field';
        }
        if (this.hasNoField()) {
          return 'noField';
        }
      }
      hasValue() {
        return this.value && !this.template && !this.templateUrl;
      }
      hasTemplate() {
        return this.template && !this.value && !this.templateUrl;
      }
      hasTemplateUrl() {
        return this.templateUrl && !this.value && !this.template;
      }
      hasField() {
        return this.field && !this.templateUrl && !this.value && !this.template;
      }
      hasNoField() {
        return !this.field && !this.templateUrl && !this.value && !this.template;
      }
    }
    return TableColumn;
  });
