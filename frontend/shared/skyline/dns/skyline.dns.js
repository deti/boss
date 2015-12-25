export default angular.module('skyline.dns', [
  require('./dns.list.state').default.name,
  require('./dns.new.state').default.name,
  require('./dns.records.state').default.name,
  require('./dns.record.new.state').default.name,
  require('./dns.record.edit.state').default.name
]);
