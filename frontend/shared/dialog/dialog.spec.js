import './dialog';

describe('dialog', function () {
  var dialog, $modal, scope;

  beforeEach(angular.mock.module('boss.dialog'));

  beforeEach(inject(function (_dialog_, _$modal_) {
    dialog = _dialog_;
    $modal = _$modal_;
    spyOn($modal, 'open').and.callFake(function (conf) {
      scope = {};
      conf.controller[1](scope);
      return conf.controller;
    });
  }));

  it('should show confirm dialog', function () {
    dialog.confirm('hello');
    expect($modal.open)
      .toHaveBeenCalledWith({template: jasmine.any(String), controller: jasmine.any(Array)});
    expect(scope.header).toBe('hello');
    expect(scope.buttonYesText).toBe('Yes');
    expect(scope.buttonNoText).toBe('Cancel');
  });

  it('should show alert dialog', function () {
    dialog.alert('hello');
    expect($modal.open)
      .toHaveBeenCalledWith({template: jasmine.any(String), controller: jasmine.any(Array)});
    expect(scope.header).toBe('hello');
    expect(scope.buttonText).toBe('Ok');
  });
});
