const dependencies = [];

export default angular.module('boss.urlParser', dependencies)
  .factory('URLParser', function ($document) {
    class URLParser {
      constructor(url) {
        this._parser = $document[0].createElement('a');
        this._parser.href = url;
      }

      searchParam(name, defaultValue = undefined) {
        var params = this.searchParams;
        if (typeof params[name] !== 'undefined') {
          return params[name];
        }
        return defaultValue;
      }

      get url() {
        return this._parser.href;
      }

      set url(val) {
        this._parser.href = val;
      }

      get searchParams() {
        var search = this.search.substr(1),
          paramsStrings = search.split('&'),
          params = {};

        paramsStrings.forEach(param => {
          if (!param) {
            return;
          }
          var arr = param.split('=');
          if (arr.length > 1) {
            params[arr[0]] = arr[1];
          } else {
            params[arr[0]] = true;
          }
        });
        return params;
      }

      get protocol() {
        return this._parser.protocol;
      }

      get hostname() {
        return this._parser.hostname;
      }

      get port() {
        return this._parser.port;
      }

      get host() {
        return this._parser.host;
      }

      get pathname() {
        return this._parser.pathname;
      }

      get search() {
        return this._parser.search;
      }

      get hash() {
        return this._parser.hash;
      }
    }
    return URLParser;
  });
