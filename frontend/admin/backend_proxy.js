var url = require('url');
var proxy = require('proxy-middleware');
var http = require('http');
var connect = require('connect');
var app = connect();

function getProxyMiddlewareProducer(baseUrl) {
  return function (route) {
    var proxyOptions = url.parse(baseUrl + '/' + route);
    proxyOptions.cookieRewrite = true;
    return proxy(proxyOptions);
  }
}

module.exports = function createBackendProxy(backendUrl, proxyPath, port) {
  var proxyProducer = getProxyMiddlewareProducer(backendUrl);
  proxyPath.forEach(function (url) {
    app.use('/' + url, proxyProducer(url));
  });

  http
    .createServer(app)
    .listen(port);
};

