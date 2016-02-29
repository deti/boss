import './bsTableFilter';

describe('bsTableFilter', function () {
  var element, scope, form, $state, $stateParams, $timeout, $compile, $rootScope;

  var tableState;

  function tableCtrl() {
    this.tableState = function () {
      return tableState;
    };
    this.pipe = function () {
    };
  }

  function recompileForm() {
    scope = $rootScope.$new();
    element = '<div st-table="data"><bs-table-filter search-tags="searchTags" filters="filters" state-name="currency"></bs-table-filter></div>';
    element = $compile(element)(scope);
    element.appendTo(document.body);
    form = scope.form;
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

  beforeEach(inject(function (_$state_, _$stateParams_, _$timeout_, _$rootScope_, _$compile_) {
    $state = _$state_;
    $stateParams = _$stateParams_;
    $timeout = _$timeout_;
    $rootScope = _$rootScope_;
    $compile = _$compile_;
    Object.keys($stateParams).forEach(key => {
      delete $stateParams[key];
  });
  }));

  afterEach(function () {
    element.remove();
  });

  it('shouldn\'t activate input if stateParam page is set', function () {
    $stateParams.filterActive = true;
    $stateParams.page = 2;
    recompileForm();
    scope.$digest();
    var input = element.find('input');
    $timeout.flush();
    scope.$digest();
    expect(input[0]).not.toBe(document.activeElement);
  });

  it('should add predicate objects to tableState if there is text search in stateParams', function () {
    $stateParams.text = 'test';
    recompileForm();
    scope.$digest();
    expect(typeof tableState.search.predicateObject).toBe('function');
    var item1 = {name: 'test'},
      item2 = {name: 'not pass'};
    expect(tableState.search.predicateObject(item1)).toBe(true);
    expect(tableState.search.predicateObject(item2)).toBe(false);
  });

  it('should add predicateObject to tableState if there is multiple text search in state params', function () {
    $stateParams.text = ['foo', 'bar'];
    recompileForm();
    scope.$digest();
    expect(typeof tableState.search.predicateObject).toBe('function');
    var item1 = {name: 'foo', last_name: 'bar'},
      item2 = {name: 'not pass', last_name: 'bar'};
    expect(tableState.search.predicateObject(item1)).toBe(true);
    expect(tableState.search.predicateObject(item2)).toBe(false);
  });
});
