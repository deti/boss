import './bsTablePagination';

describe('bsTablePagination', function () {
  var element, $scope, $stateParams, $state, $compile;

  beforeEach(function () {
    angular.mock.module('boss.tablePagination');
  });

  beforeEach(inject(function (_$compile_, $rootScope, _$stateParams_, _$state_) {
    $scope = $rootScope;
    element = angular.element(
      '<bs-table-pagination pages="pages" state-name="main"></bs-table-pagination>'
    );
    $stateParams = _$stateParams_;
    $state = _$state_;
    $compile = _$compile_;
  }));

  function pagesFromElement(element) {
    var links = element.find('li > a').toArray();
    links.splice(0, 1);
    links.splice(links.length - 1, 1);

    return links.map(i => i.innerText);
  }

  it('should show links to 5 pages when current page is first', function () {
    $scope.pages = 11;
    $stateParams.page = 1;
    $compile(element)($scope);
    $scope.$digest();

    var links = pagesFromElement(element);
    expect(links).toEqual(['1', '2', '3', '4', '5']);
  });

  it('should show links to 5 pages when current page is in the middle of pages', function () {
    $scope.pages = 11;
    $stateParams.page = 5;
    $compile(element)($scope);
    $scope.$digest();

    var links = pagesFromElement(element);
    expect(links).toEqual(['3', '4', '5', '6', '7']);
  });

  it('should show links to 5 pages when current page is last', function () {
    $scope.pages = 11;
    $stateParams.page = 11;
    $compile(element)($scope);
    $scope.$digest();

    var links = pagesFromElement(element);
    expect(links).toEqual(['7', '8', '9', '10', '11']);
  });

  it('should render shorter pagination when there is less than 5 pages', function () {
    $scope.pages = 3;
    $stateParams.page = 1;
    $compile(element)($scope);
    $scope.$digest();

    var links = pagesFromElement(element);
    expect(links).toEqual(['1', '2', '3']);
  });

  it('should navigate to page', function () {
    $scope.pages = 11;
    $stateParams.page = 1;
    $compile(element)($scope);
    $scope.$digest();
    spyOn($state, 'go');
    element.find('li:eq(3) > a').parent().click();
    expect($state.go).toHaveBeenCalledWith('main', {page: 3});
  });
});
