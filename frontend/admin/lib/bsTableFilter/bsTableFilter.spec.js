import './bsTableFilter';

describe('bsTableFilter', function () {
  var element, scope, form, $state, $stateParams, $timeout;

  var tableState;

  function tableCtrl() {
    this.tableState = function () {
      return tableState
    };
    this.pipe = function () {
    };
  }

  beforeEach(function () {
    tableState = {
      search: {}
    };
  });

  beforeEach(function () {
    angular.mock.module('boss.tableFilter', function ($controllerProvider) {
      $controllerProvider.register('stTableController', tableCtrl);
    });
  });

  beforeEach(inject(function (_$state_, _$stateParams_, _$timeout_) {
    $state = _$state_;
    $stateParams = _$stateParams_;
    $timeout = _$timeout_;
    Object.keys($stateParams).forEach(key => {
      delete $stateParams[key];
    })
  }));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    element = '<div st-table="data"><bs-table-filter search-tags="searchTags" filters="filters" state-name="currency"></bs-table-filter></div>';
    element = $compile(element)(scope);
    element.appendTo(document.body);
    form = scope.form;
  }));

  afterEach(function () {
    element.remove();
  });

  it('shouldn\'t activate input if stateParam page is set', function () {
    $stateParams.filterActive = true;
    $stateParams.page = 2;
    scope.$digest();
    var input = element.find('input');
    $timeout.flush();
    scope.$digest();
    expect(element.find('input')[0]).not.toBe(document.activeElement);
  });

  it('should add predicate objects to tableState if there is text search in stateParams', function () {
    $stateParams.text = 'test';
    scope.$digest();
    expect(typeof tableState.search.predicateObject).toBe('function');
    var item1 = {name: 'test'},
      item2 = {name: 'not pass'};
    expect(tableState.search.predicateObject(item1)).toBe(true);
    expect(tableState.search.predicateObject(item2)).toBe(false);
  });

  it('should add predicateObject to tableState if there is multiple text search in state params', function () {
    $stateParams.text = ['foo', 'bar'];
    scope.$digest();
    expect(typeof tableState.search.predicateObject).toBe('function');
    var item1 = {name: 'foo', last_name: 'bar'},
      item2 = {name: 'not pass', last_name: 'bar'};
    expect(tableState.search.predicateObject(item1)).toBe(true);
    expect(tableState.search.predicateObject(item2)).toBe(false);
  });

  it('should parse state params filters', function () {
    $stateParams.status = 'active';
    scope.filters = [{
      property: 'status',
      title: 'status',
      options: [{text: 'active', val: 'active'}, {text: 'blocked', val: 'blocked'}]
    }];
    scope.$digest();
    expect(element.find('.tag-list').children().length).toBe(1);
    expect(element.find('.tag-list').find('span').text()).toBe('active');
  });
});
