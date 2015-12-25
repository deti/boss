import './bsPhoneInput';

describe('bsPhoneInput', function () {
  var element, scope, form, input;
  beforeEach(angular.mock.module('boss.phoneInput'));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    element = '<form name="form">\n  <input type="text" ng-model="foo" name="foo" bs-phone-input>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
    input = element.find('input');
  }));

  it('should remove all not numeric symbols from value', function () {
    form.foo.$setViewValue('bla-bla123');
    scope.$digest();
    expect(scope.foo).toBe('123');
  });

  it('should set invalid to false if input value is empty', function () {
    form.foo.$setViewValue('');
    scope.$digest();
    expect(form.foo.$invalid).toBe(false);
  });

  it('should mark input as invalid if there is less than 4 symbols', function () {
    form.foo.$setViewValue('1234');
    scope.$digest();
    expect(form.foo.$invalid).toBe(true);

    form.foo.$setViewValue('12345');
    scope.$digest();
    expect(form.foo.$invalid).toBe(false);
  });

  it('should mark input as invalid if there is less than 10 symbols and value starts with +', function () {
    form.foo.$setViewValue('+7999888776');
    scope.$digest();
    expect(form.foo.$invalid).toBe(true);

    form.foo.$setViewValue('+79998887766');
    scope.$digest();
    expect(form.foo.$invalid).toBe(false);
  });
});
