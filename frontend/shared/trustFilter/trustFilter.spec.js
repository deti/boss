import './trustFilter';

describe('trustFilter', function () {
  var element, scope;

  beforeEach(angular.mock.module('boss.trustFilter'));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    scope.html = '';
    scope.submit = function () {};
    element = '<span ng-bind-html="html|trust"></span>';
    element = $compile(element)(scope);
  }));

  it('should allow to insert html in template', function () {
    scope.html = '<div>Test</div>';
    scope.$digest();
    expect(element.find('div').length).toBe(1);
    expect(element.find('div').text()).toBe('Test');
  });
});
