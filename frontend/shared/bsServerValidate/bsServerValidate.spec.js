import './bsServerValidate';

describe('bsServerValidate', function () {
  var element, scope, form, popupErrorService;
  beforeEach(angular.mock.module('boss.serverValidate'));

  beforeEach(inject(function ($rootScope, $compile, _popupErrorService_) {
    popupErrorService = _popupErrorService_;
    spyOn(popupErrorService, 'show');

    scope = $rootScope.$new();
    element = '<form name="form" bs-server-validate="{400: \'TestError\'}">\n  <input type="text" ng-model="foo" name="foo">\n</form>';
    element = $compile(element)(scope);
    scope.$digest();
    form = scope.form;
  }));

  it('should pass a dummy test', function () {
    expect(form).toBeTruthy();
  });

  it('should add parseErrors method to form', function () {
    expect(form.$parseErrors).toBeDefined();
    expect(typeof form.$parseErrors).toBe('function');
  });

  it('should parse error without field and add unclassified error', function () {
    var rsp = {
      data: {
        localized_message: 'bla error',
        message: 'foo error'
      }
    };
    form.$parseErrors(rsp);
    expect(form.$error.unclassified).toBeDefined();
    expect(form.$server_unclassified).toBe('bla error');
  });

  it('should parse error and define field based on start of message', function () {
    var rsp = {
      data: {
        localized_message: 'foo ошибка',
        message: 'foo error'
      }
    };
    form.$parseErrors(rsp);
    expect(form.foo.$error.server).toBeDefined();
    expect(form.foo.$error.server).toBe(true);
    expect(form.foo.$server_error).toBeDefined();
    expect(form.foo.$server_error).toBe('ошибка');
  });

  it('should parse error based on status', function () {
    var rsp = {
      status: 500,
      data: {
        localized_message: 'ошибка',
        message: 'error'
      }
    };
    form.$parseErrors(rsp);
    expect(form.$error.ServerError).toBeDefined();
    expect(form.$server_error_ServerError).toBeDefined();
    expect(form.$server_error_ServerError).toBe('ошибка');
  });

  it('should parse error based on status from directive attribute', function () {
    var rsp = {
      status: 400,
      data: {
        localized_message: 'ошибка',
        message: 'error'
      }
    };
    form.$parseErrors(rsp);
    expect(form.$error.TestError).toBeDefined();
    expect(form.$server_error_TestError).toBeDefined();
    expect(form.$server_error_TestError).toBe('ошибка');
  });

  it('should parse errors with field param', function () {
    var rsp = {
      data: {
        localized_message: 'ошибка',
        message: 'error',
        field: 'foo'
      }
    };
    form.$parseErrors(rsp);
    expect(form.foo.$error.server).toBeDefined();
    expect(form.foo.$error.server).toBe(true);
    expect(form.foo.$server_error).toBeDefined();
    expect(form.foo.$server_error).toBe('ошибка');
  });

  it('should parse error with dot-separated field param', function () {
    var rsp = {
      data: {
        localized_message: 'ошибка',
        message: 'error',
        field: 'some.prefix.foo'
      }
    };
    form.$parseErrors(rsp);
    expect(form.foo.$error.server).toBeDefined();
    expect(form.foo.$error.server).toBe(true);
    expect(form.foo.$server_error).toBeDefined();
    expect(form.foo.$server_error).toBe('ошибка');
  });

  it('should show popup error if field is not on the form', function () {
    var rsp = {
      data: {
        localized_message: 'ошибка',
        message: 'error',
        field: 'bar'
      }
    };
    form.$parseErrors(rsp);
    expect(popupErrorService.show).toHaveBeenCalled();
  });

  it('should show popup error for rsp without "field" field', function () {
    var rsp = {
      data: {
        localized_message: 'bar ошибка',
        message: 'bar error'
      }
    };
    form.$parseErrors(rsp);
    expect(popupErrorService.show).toHaveBeenCalled();
  });

  it('should clear server error with http-code on input change', function () {
    var rsp = {
      data: {
        status: 400,
        localized_message: 'ошибка',
        message: 'error'
      }
    };
    form.$parseErrors(rsp);
    form.foo.$setViewValue('test');
    expect(form.$error.TestError).toBeUndefined();
  });

  it('should work if error message from server is empty', function () {
    var rsp = {
      data: {
        localized_message: 'ошибка',
        message: ''
      }
    };
    form.$parseErrors(rsp);
    expect(form.$error.unclassified).toBeDefined();
    expect(form.$server_unclassified).toBeDefined();
    expect(form.$server_unclassified).toBe('ошибка');
  });
});
