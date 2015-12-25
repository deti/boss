module.exports = function(config) {
  return {
    dev: {
      options: {
        port: 9999,
        hostname: '127.0.0.1',
        base: config.srcDir,
        keepalive: true
      }
    },
    dist: {
      options: {
        port: 5605,
        hostname: '*',
        base: config.destDir,
        keepalive: true
      }
    },
  }
};
