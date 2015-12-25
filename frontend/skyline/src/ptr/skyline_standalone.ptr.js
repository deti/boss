export default angular.module('skyline_standalone.ptr', [
  require('../../../shared/skyline/ptr/ptr.list.state').default.name,
  require('../../../shared/skyline/ptr/ptr.edit.state').default.name,
  require('./skyline_standalone.ptr.new').default.name
]);
