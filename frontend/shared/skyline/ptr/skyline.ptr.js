export default angular.module('skyline.ptr', [
  require('./ptr.list.state').default.name,
  require('./ptr.new.state').default.name,
  require('./ptr.edit.state').default.name
]);
