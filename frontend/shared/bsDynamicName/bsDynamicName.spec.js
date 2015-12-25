import './bsDynamicName';

describe('dynamicName', function () {
  var element, scope, form;
  beforeEach(angular.mock.module('boss.dynamicName'));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    scope.array = ['dynamic', 'other'];
    element = '<form name="form">\n  <div ng-repeat="name in array">\n    <input type="text" ng-model="foo" name="{{name}}" bs-dynamic-name>\n  </div>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
  }));

  it('should add input to form controller', function () {
    expect(form.dynamic).toBeDefined();
    expect(form.other).toBeDefined();
  });
});
