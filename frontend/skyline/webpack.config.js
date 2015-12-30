require('es6-promise').polyfill();
var path = require('path');
var fs = require('fs');
var backendProxy = require('./backend_proxy');
var appConfig = require('./config');

var node_modules = path.resolve(__dirname, './node_modules');
var backendProxyPort = 5001;
var proxyPath = ['keystone', 'nova', 'cinder', 'neutron', 'glance', 'mistral', 'designate'];

var config = {
  entry: [
    path.resolve(__dirname, 'src/app.js'),
    path.resolve(__dirname, 'src/index.html'),
    path.resolve(__dirname, 'node_modules/angular-i18n/angular-locale_ru-ru.js'),
    path.resolve(__dirname, 'node_modules/angular-i18n/angular-locale_en-us.js')
  ],
  output: {
    path: path.resolve(__dirname, 'bin/' + appConfig.relativePath),
    publicPath: '/' + appConfig.relativePath + '/',
    filename: 'app.js'
  },
  module: {
    loaders: [
      {
        test: /\.js$/,
        loader: 'ng-annotate',
        exclude: /node_modules/
      },
      {
        test: /\.js$/,
        loader: 'babel',
        query: {
          presets: [path.resolve(node_modules, 'babel-preset-stage-1'), path.resolve(node_modules, 'babel-preset-es2015')],
          plugins: [path.resolve(node_modules, 'babel-plugin-transform-class-properties')]
        },
        exclude: /node_modules/
      },
      {
        // translation files
        test: /\.i18n\.json$/,
        loader: 'raw'
      },
      {
        // partial templates, that will be used in ng-include
        test: /\.partial\.tpl\.html$/,
        loaders: ['ngtemplate?relativeTo=/' + path.resolve(__dirname, '..') + '/', 'html']
      },
      {
        // normal templates, that will be used in template: '...'
        test: /\.tpl\.html$/,
        exclude: /\.partial\.tpl\.html$/,
        loaders: ['raw']
      },
      {
        // index.html file
        test: /\.html$/,
        exclude: /\.tpl\.html$/,
        loaders: ['html', 'file?name=[name].[ext]']
      },
      {
        // angular locale files
        test: /angular-locale_[a-z\-]*\.js$/,
        loader: 'file?name=[name].[ext]'
      },
      {
        test: /zxcvbn\.js/,
        loader: 'file?name=[name].[ext]'
      },
      {
        // favicon
        test: /favicon\.ico$/,
        loader: 'file?name=[name].[ext]'
      },
      {
        // assets
        test: /\.woff|eot|woff2|ttf|svg|ico|png|swf$/,
        exclude: /favicon\.ico/,
        loader: 'file'
      },
      {
        // less files
        test: /\.less$/,
        loaders: ['style', 'css', 'autoprefixer', 'less']
      },
      {
        test: /\.css$/,
        loaders: ['style', 'css']
      },
      {
        test: /jquery\.js$/,
        loaders: ['expose?$', 'expose?jQuery']
      },
      {
        test: /ZeroClipboard\.js$/,
        loader: 'expose?ZeroClipboard'
      }
    ],
    noParse: []
  },
  resolveLoader: {
    root: path.resolve('node_modules')
  },
  resolve: {
    alias: {}
  },
  devServer: {
    port: 5000,
    historyApiFallback: {
      index: '/' + appConfig.relativePath + '/index.html'
    },
    contentBase: 'bin/',
    publicPath: '/' + appConfig.relativePath + '/',
    proxy: {}
  },
  addVendor: function (name, path) {
    this.resolve.alias[name] = path;
    this.module.noParse.push(new RegExp(path));
  },
  addProxy: function (path) {
    this.devServer.proxy['/' + path + '*'] = {
      target: 'http://localhost:' + backendProxyPort,
      secure: false
    };
  }
};

config.addVendor('moment', node_modules + '/moment/min/moment.min.js');
config.addVendor('cron-to-text', node_modules + '/cron-to-text/dist/cron-to-text.min.js');

if (process.env.DEV) {
  var backendUrl = require('./backend.config'),
    selectedBackend = backendUrl.local;
  if (process.env.BACKEND) {
    if (fs.existsSync('./backend.config.local.js')) {
      var _ = require('lodash');
      backendUrl = _.assign({}, backendUrl, require('./backend.config.local'));
    }
    if (!backendUrl[process.env.BACKEND]) {
      console.error('There is no "%s" backend defined in backend.config.js or backend.config.local', process.env.DEV);
      return;
    }
    selectedBackend = backendUrl[process.env.BACKEND];
  }

  console.log('Will proxy requests to', selectedBackend);
  proxyPath.forEach(function (item) {
    config.addProxy(item);
  });
  backendProxy(selectedBackend, proxyPath, backendProxyPort);
}


module.exports = config;
