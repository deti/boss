const dependencies = [];

export default angular.module('boss.openstackService.OSCredentials', dependencies)
  .constant('OS_CRED_UPDATE', 'openstackService.OSCredentials.update')
  .factory('OSCredentials', function ($rootScope, OS_CRED_UPDATE) {
    var token = token;
    var tenantId = tenantId;
    return {
      get token() {
        return token;
      },
      set token(val) {
        token = val;
        $rootScope.$emit(OS_CRED_UPDATE);
      },
      get tenantId() {
        return tenantId;
      },
      set tenantId(val) {
        tenantId = val;
        $rootScope.$emit(OS_CRED_UPDATE);
      }
    };
  });
