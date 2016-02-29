import './bsFormSaver';

describe('bsFormSaver', function () {
  var element, scope, form, $body, $timeout;

  beforeEach(angular.mock.module('boss.formSaver'));

  beforeEach(angular.mock.inject(function ($rootScope, $compile, $document, _$timeout_) {
    $body = angular.element($document[0].body);
    $timeout = _$timeout_;

    scope = $rootScope.$new();
    scope.foo = '';
    scope.submit = function () {};
    element = '<form ng-submit="submit();" name="form" bs-form-saver>\n  <input type="text" name="foo" ng-model="foo">\n  <button id="submit" type="submit"></button>\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    $timeout.flush();
    form = scope.form;
  }));

  afterEach(function () {
    scope.$destroy();
  });

  it('should add fake submit button to form', function () {
    expect(element.find('button[type=submit]').length).toBe(2);
    expect($body.find('.popup').length).toBe(1);
    expect($body.find('.popup').hasClass('ng-hide')).toBe(true);
  });

  it('should remove template on scope destroy', function () {
    scope.$destroy();
    expect($body.find('.popup').length).toBe(0);
  });

  it('should show saver when one of input was changed', function () {
    form.foo.$setDirty();
    scope.$digest();
    expect($body.find('.popup').hasClass('ng-hide')).toBe(false);
  });

  it('should restore input values', function () {
    form.foo.$setDirty();
    form.foo.$setViewValue('test');
    scope.$digest();
    expect(scope.foo).toBe('test');
    $body.find('.popup').find('button')[1].click();
    expect(scope.foo).toBe('');
  });

  it('should reset all saved values on form submit', function () {
    form.foo.$setDirty();
    form.foo.$setViewValue('test');
    scope.$digest();
    element.find('#submit').click();
    scope.$digest();
    expect($body.find('.popup').hasClass('ng-hide')).toBe(true);
  });

  it('should show saver when previous change set input to dirty but not changed value', function () {
    form.foo.$setDirty();
    scope.$digest();
    $body.find('.popup').find('button')[1].click();
    expect($body.find('.popup').hasClass('ng-hide')).toBe(true);
    form.foo.$setDirty();
    scope.$digest();
    expect($body.find('.popup').hasClass('ng-hide')).toBe(false);
  });
});
