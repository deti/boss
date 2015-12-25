import './bsCompileTemplate';

describe('bsCompileTemplate', function () {
  beforeEach(angular.mock.module('boss.compileTemplate'));

  it('should compile template and insert it', inject(function ($rootScope, $compile) {
    var scope = $rootScope.$new();
    scope.item = {
      value: 'foo'
    };
    var element = '<div bs-compile-template="\'{{item.value}}\'"></div>';
    element = $compile(element)(scope);
    scope.$digest();

    expect(element.text()).toBe('foo');
  }));
});
