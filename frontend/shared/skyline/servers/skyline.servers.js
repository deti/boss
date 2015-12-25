export default angular.module('skyline.servers', [
  require('./server.list.state').default.name,
  require('./server.new.state').default.name,
  require('./server.edit.state').default.name,
  require('./server.vns.state').default.name
]);
