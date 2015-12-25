import './textPreview';

describe('textPreview service', function () {
  var textPreview;
  beforeEach(angular.mock.module('boss.textPreview'));

  beforeEach(inject(function (_textPreview_) {
    textPreview = _textPreview_;
  }));

  it('Should pass dummy test', function () {
    expect(textPreview).toBeTruthy();
  });

  it('Should break text to two parts', function () {
    var text = 'bla bla bla';
    var res = textPreview(text, 4);

    expect(res.main).toBeDefined();
    expect(res.rest).toBeDefined();
    expect(res.main).toBe('bla');
    expect(res.rest).toBe('bla bla');
  });

  it('shouldn\'t break words', function () {
    var text = 'bla bla bla';
    var res = textPreview(text, 6);

    expect(res.main).toBeDefined();
    expect(res.rest).toBeDefined();
    expect(res.main).toBe('bla');
    expect(res.rest).toBe('bla bla');
  });

  it('should return empty rest when string shorter than limit', function () {
    var text = 'bla';
    var res = textPreview(text, 4);

    expect(res.main).toBe('bla');
    expect(res.rest).toBe('');
  });
});
