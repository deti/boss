const dependencies = [
];

export default angular.module('boss.openstackService.Keystone', dependencies)
  .value('KEYSTONE_BASE_URL', '/keystone/v3')
  .factory('Keystone', function ($http, KEYSTONE_BASE_URL, $q) {
    var pair = null;
    class Keystone {
      constructor(baseUrl) {
        this.baseUrl = baseUrl;
      }

      authenticate(login, password) {
        return $http({
          method: 'POST',
          url: `${this.baseUrl}/auth/tokens`,
          data: {
            auth: {
              identity: {
                methods: ['password'],
                password: {
                  user: {
                    domain: {id: 'default'},
                    name: login,
                    password: password
                  }
                }
              }
            }
          }
        })
        .then(r => {
          if (!r.data.token || !r.data.token.project || !r.data.token.project.id) {
            return $q.reject('No project.id in keystone response');
          }
          this.authPair = {
            token: r.headers('x-subject-token'),
            tenantId: r.data.token.project.id
          };
          return this.authPair;
        });
      }

      set authPair(val) {
        pair = val;
      }
      get authPair() {
        return pair;
      }

      projects(token, marker = null, limit = null) {
        return $http({
          method: 'GET',
          url: `${this.baseUrl}/projects`,
          params: {marker, limit},
          headers: {
            'X-Auth-Token': token
          }
        })
        .then(r => r.data);
      }

      users(token, marker = null, limit = null) {
        return $http({
          method: 'GET',
          url: `${this.baseUrl}/users`,
          params: {marker, limit},
          headers: {
            'X-Auth-Token': token
          }
        })
        .then(r => r.data);
      }
    }

    return new Keystone(KEYSTONE_BASE_URL);
  });
