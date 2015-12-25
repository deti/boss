import './fileSaver';

describe('fileSaver', function () {
  var fileSaver;
  beforeEach(angular.mock.module('boss.fileSaver'));

  beforeEach(inject(function (_fileSaver_) {
    fileSaver = _fileSaver_;
  }));

  it('should create html form from httpConfig', function () {
    var config = {
      url: '/test',
      method: 'post',
      data: {
        foo: 'foo val',
        bar: 'bar val'
      }
    };
    var form = fileSaver.createForm(config),
      inputs = form.find('input');
    expect(form.attr('action')).toBe('/test');
    expect(form.attr('method')).toBe('post');
    expect(inputs.length).toBe(2);
    expect($(inputs[0]).attr('name')).toBe('foo');
    expect($(inputs[1]).attr('name')).toBe('bar');
    expect($(inputs[0]).attr('value')).toBe('foo val');
    expect($(inputs[1]).attr('value')).toBe('bar val');
  });

  it('should submit form', function () {
    var fakeForm = {
      submit: function () {},
      remove: function () {}
    };
    spyOn(fileSaver, 'createForm').and.returnValue(fakeForm);
    spyOn(fakeForm, 'submit').and.returnValue(fakeForm);
    spyOn(fakeForm, 'remove');
    fileSaver.saveFileFromHttp({});
    expect(fakeForm.submit).toHaveBeenCalled();
    expect(fakeForm.remove).toHaveBeenCalled();
  });
});
