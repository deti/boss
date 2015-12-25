import './TableColumn';

describe('TableColumn', function () {
  var TableColumn;
  beforeEach(angular.mock.module('boss.table.TableColumn'));

  beforeEach(inject(function (_TableColumn_) {
    TableColumn = _TableColumn_;
  }));

  beforeEach(inject(function (appLocale) {
    spyOn(appLocale, 'getLang').and.returnValue('en');
  }));

  it('should pass a dummy test', function () {
    expect(TableColumn).toBeTruthy();
  });

  it('should choose correct sorting field', function () {
    var column = new TableColumn({field: 'detailed_info.name', title: '123'});
    expect(column.usedSortField).toEqual('detailed_info.name');
  });

  it('should choose correct sorting field when localized filter used', function () {
    var column = new TableColumn({field: 'detailed_info.name', title: '123', filter: 'localizedName'});
    expect(column.usedSortField).toEqual('detailed_info.name.localized_name.en');
  });

  it('should choose correct sorting field when localized filter with other filters', function () {
    var column = new TableColumn({field: 'detailed_info.name', title: '123', filter: ['localizedName', 'date']});
    expect(column.usedSortField).toEqual('detailed_info.name.localized_name.en');
  });

  it('should choose correct sorting field when localized filter in object notation used', function () {
    var column = new TableColumn({field: 'detailed_info.name', title: '123', filter: {name: 'localizedName', args: ['localized_description']}});
    expect(column.usedSortField).toEqual('detailed_info.name.localized_description.en');
  });

  it('should allow use function to define sort field', function () {
    var column = new TableColumn({field: 'detailed_info', title: '123', sortField: function () {
      return 'field';
    }});
    expect(column.usedSortField).toEqual('field');
  });

  it('should return correct field type', function () {
    var column = new TableColumn({title: '123'});
    expect(column.type).toBe('noField');
    column = new TableColumn({title: '123', value: '1'});
    expect(column.type).toBe('value');
    column = new TableColumn({title: '123', template: '1'});
    expect(column.type).toBe('template');
    column = new TableColumn({title: '123', templateUrl: '1'});
    expect(column.type).toBe('templateUrl');
  });
});
