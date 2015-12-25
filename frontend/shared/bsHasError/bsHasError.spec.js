import './bsHasError';

describe('bsHasError', function () {
  var element, scope, form;
  beforeEach(angular.mock.module('boss.hasError'));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    element = '<form name="form">\n  <div bs-has-error id="wrapper">\n    <input type="number" name="test" class="form-control" ng-model="someName">\n  </div>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
  }));

  it('should add has-error class invalid dirty input wrapper', function () {
    form.test.$setValidity('server', false);
    form.test.$setDirty();
    scope.$digest();
    var wrapper = element.find('#wrapper');
    expect(wrapper.hasClass('has-error')).toBe(true);
  });

  it('should remove has-error class from wrapper on validity change', function () {
    form.test.$setValidity('server', false);
    form.test.$setDirty();
    scope.$digest();

    form.test.$setValidity('server', true);
    scope.$digest();
    var wrapper = element.find('#wrapper');
    expect(wrapper.hasClass('has-error')).toBe(false);
  });

  it('should throw error when no input presented inside container', inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    var html = '<form name="form">\n  <div bs-has-error id="wrapper">\n  </div>\n</form>';
    var compile = function () {
      $compile(html)(scope);
    };
    expect(compile).toThrow();
  }));

  it('should be able to use another condition to show error', inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    var html = '<form name="form">\n  <div bs-has-error="anotherCondition" id="wrapper">\n    <input type="number" name="test" class="form-control" ng-model="someName">\n  </div>\n</form>';
    scope.anotherCondition = false;
    element = $compile(html)(scope);
    scope.$digest();
    var wrapper = element.find('#wrapper');
    expect(wrapper.hasClass('has-error')).toBe(false);

    scope.anotherCondition = true;
    scope.$digest();
    expect(wrapper.hasClass('has-error')).toBe(true);
  }));

  it('should use target with other selector', inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    var html = '<form name="form">\n  <div bs-has-error has-error-target="\'#target\'" id="wrapper">\n    <input type="number" name="test" id="target" ng-model="someName">\n  </div>\n</form>';
    element = $compile(html)(scope);
    scope.$digest();
    form = scope.form;
    form.test.$setValidity('server', false);
    form.test.$setDirty();
    scope.$digest();
    var wrapper = element.find('#wrapper');

    expect(wrapper.hasClass('has-error')).toBe(true);
  }));
});
