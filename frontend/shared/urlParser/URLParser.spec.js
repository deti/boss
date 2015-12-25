import './urlParser';

describe('URLParser', function () {
  var URLParser;
  const url = 'http://example.com:3000/pathname/?search=test&bool&another=a#hash';
  beforeEach(angular.mock.module('boss.urlParser'));

  beforeEach(inject(function (_URLParser_) {
    URLParser = _URLParser_;
  }));

  it('should parse url', function () {
    var parser = new URLParser(url);

    expect(parser.protocol).toBe('http:');
    expect(parser.hostname).toBe('example.com');
    expect(parser.port).toBe('3000');
    expect(parser.host).toBe('example.com:3000');
    expect(parser.pathname).toBe('/pathname/');
    expect(parser.search).toBe('?search=test&bool&another=a');
    expect(parser.hash).toBe('#hash');
  });

  it('should parse search params and allow to access it in object-like', function () {
    var parser = new URLParser(url),
      searchParams = parser.searchParams;

    expect(searchParams).toEqual({
      search: 'test',
      another: 'a',
      bool: true
    });
  });

  it('should allow to access one url param', function () {
    var parser = new URLParser(url);

    expect(parser.searchParam('search')).toBe('test');
    expect(parser.searchParam('bool')).toBe(true);
    expect(parser.searchParam('undefined')).toEqual(undefined);
  });
});
