const dependencies = [
  require('./Nova').default.name,
  require('./Glance').default.name,
  require('./Cinder').default.name,
  require('./Mistral').default.name,
  require('./Designate').default.name,
  require('./Neutron').default.name,
  require('./DesignateV2').default.name,
  require('./OSCredentials').default.name
];

export default angular.module('boss.openstackService', dependencies)
  .factory('OSService', function (Nova, Glance, Cinder, Mistral, Designate, Neutron, DesignateV2, OSCredentials) {
    var modules = {};
    function getModules({token, tenantId}) { // TODO: get rid of this
      OSCredentials.token = token;
      OSCredentials.tenantId = tenantId;
      modules.Nova = Nova;
      modules.Glance = Glance;
      modules.Cinder = Cinder;
      modules.Mistral = Mistral;
      modules.Neutron = Neutron;
      modules.Designate = Designate;
      modules.DesignateV2 = DesignateV2;
      return modules;
    }

    return {
      getModules: getModules,
      modules: modules
    };
  });
