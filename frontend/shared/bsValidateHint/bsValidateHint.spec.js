import './bsValidateHint';

describe('bsValidateHint', function () {
  var element, scope, form, input;
  beforeEach(angular.mock.module('boss.validateHint'));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    element = '<form name="form">\n  <input type="text" ng-model="foo" name="foo" bs-validate-hint>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
    input = element.find('input');
  }));

  it('should append errorMessage element', function () {
    expect(element.find('.errorMessage').length).toBe(1);
  });

  it('should add error message', function () {
    form.foo.$setValidity('required', false);
    input.blur();
    scope.$digest();
    expect(element.find('.errorMessage').text()).toBe('This field is mandatory');
  });

  it('shouldn\'t add error message before blur', function () {
    form.foo.$setValidity('required', false);

    scope.$digest();
    expect(element.find('.errorMessage').text()).toBe('');
  });

  it('should clear errorMessage', function () {
    form.foo.$setValidity('required', false);
    input.blur();
    scope.$digest();
    expect(element.find('.errorMessage').text()).toBe('This field is mandatory');

    form.foo.$setValidity('required', true);
    scope.$digest();
    expect(element.find('.errorMessage').text()).toBe('');
  });

  it('should add error message without blur event', function () {
    form.foo.$setValidity('server', false);
    form.foo.$server_error = 'message';
    scope.$digest();
    expect(element.find('.errorMessage').text()).toBe('message');
  });

  it('should correctly work with select element', inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    element = '<form name="form">\n  <div class="select">\n    <select name="foo" id="foo" ng-model="foo" bs-validate-hint></select>\n  </div>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
    input = element.find('input');
    expect(element.find('.errorMessage').length).toBe(1);
  }));
});
