var webpackConfig = require('./webpack.config');
delete webpackConfig.entry;
webpackConfig.devtool = 'inline-source-map';

module.exports = function (karma) {
  karma.set({
    basePath: './',
    files: [
      './src/vendor.js',
      './node_modules/angular-mocks/angular-mocks.js',
      '../shared/**/*.spec.js',
      './lib/**/*.spec.js'
    ],
    frameworks: ['jasmine'],
    plugins: [require('karma-webpack'), 'karma-jasmine', 'karma-phantomjs-launcher', 'karma-sourcemap-loader'],
    reporters: ['progress'],
    logLevel: karma.LOG_INFO,
    port: 9018,
    runnerPort: 9100,
    urlRoot: '/',
    autoWatch: false,
    preprocessors: {
      'src/const/const.js': ['webpack'],
      './src/vendor.js': ['webpack'],
      '../shared/**/*.spec.js': ['webpack', 'sourcemap'],
      './lib/**/*.js': ['webpack', 'sourcemap']
    },
    webpackMiddleware: {
      // webpack-dev-middleware configuration
      // i. e.
      noInfo: true
    },
    browsers: [
      'PhantomJS'
    ],
    webpack: webpackConfig
  });
};
