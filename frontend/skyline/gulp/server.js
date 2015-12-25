var url = require('url'),
  fs = require('fs'),
  path = require('path'),
  proxy = require('proxy-middleware'),
  browserSync = require('browser-sync'),

  config = require('./config');


function getMiddleware(dir, indexFile) {
  return function (req, res, next) {
    var fileName = url.parse(req.url);
    fileName = fileName.href.split(fileName.search).join('');
    var fileExists = fs.existsSync(dir + fileName);
    if (!fileExists && fileName.indexOf('browser-sync-client') < 0) {
      req.url = indexFile;
    }
    return next();
  };
}

function getProxyMiddlewareProducer(baseUrl) {
  return function (route) {
    var proxyOptions = url.parse(baseUrl + route);
    proxyOptions.route = route;
    return proxy(proxyOptions);
  }
}

function server(port, dir, baseBackendUrl, proxyRoutes) {
  dir = path.resolve(__dirname, '../', dir);
  var proxyProducer = getProxyMiddlewareProducer(baseBackendUrl);
  var indexFile = '/' + config.appConf.relativePath + '/index.html';
  var middleware = proxyRoutes.map(proxyProducer);
  middleware.push(getMiddleware(dir, indexFile));

  var browserSyncConfig = {
    notify: false,
    open: false,
    port: port,
    reloadOnRestart: true,
    logFileChanges: true,
    ghostMode: {
      clicks: false,
      forms: false
    },
    server: {
      baseDir: dir,
      middleware: middleware
    }
  };
  browserSync(browserSyncConfig);
}

module.exports = server;
