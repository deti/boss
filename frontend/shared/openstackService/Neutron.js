const dependencies = [
  require('./BaseOpenstack').default.name
];

export default angular.module('boss.openstackService.Neutron', dependencies)
  .factory('Neutron', function (BaseOpenstack) {
    class Neutron extends BaseOpenstack {
      constructor() {
        super('/neutron/v2.0/');
      }

      networks() {
        return this.loadFullList(this.Restangular.all('networks'), 'networks');
      }
    }

    return new Neutron();
  });
