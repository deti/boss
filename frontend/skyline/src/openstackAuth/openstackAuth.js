const dependencies = [
  require('../../../shared/localStorage/localStorage').default.name
];

export default angular.module('openstackAuth', dependencies)
  .factory('openstackAuth', function ($http, localStorage, $q, $rootScope) {
    const AUTH_STORAGE = 'os_auth_token';

    function auth(login, password, tenantId = null) {
      var authPair = isAuthenticated();
      if (authPair) {
        return $q.when(authPair);
      }
      return $http({
        method: 'POST',
        url: '/keystone/v2.0/tokens',
        data: {
          auth: {
            passwordCredentials: {
              username: login,
              password
            },
            tenantId: tenantId
          }
        }
      })
        .then(function (response) {
          authPair = {
            token: response.data.access.token.id,
            tenantId
          };
          return authPair;
        })
        .then(pair => {
          if (tenantId === null) {
            return checkToken(pair.token)
              .then(p => {
                localStorage.setItem(AUTH_STORAGE, false);
                return auth(login, password, p.tenantId);
              });
          }
          $rootScope.userInfo = pair;
          localStorage.setItem(AUTH_STORAGE, pair);
          return pair;
        });
    }

    function checkToken(token) {
      return $http({
        method: 'GET',
        url: '/keystone/v2.0/tenants',
        headers: {
          'X-Auth-Token': token
        }
      }).then(r => {
        var authPair = {
          tenantId: r.data.tenants[0].id,
          token
        };
        localStorage.setItem(AUTH_STORAGE, authPair);
        return authPair;
      }).catch(e => {
        localStorage.setItem(AUTH_STORAGE, false);
        return $q.reject(e); // this is still error, we don't need to stop it here
      });
    }

    function isAuthenticated() {
      var authPair = localStorage.getItem(AUTH_STORAGE, false);
      if (!authPair) {
        return false;
      }
      if (!authPair.token || !authPair.tenantId) {
        return false;
      }

      $rootScope.userInfo = authPair;
      return authPair.token;
    }

    function logout() {
      $rootScope.userInfo = {};
      localStorage.setItem(AUTH_STORAGE, false);
    }

    return {
      auth: auth,
      isAuthenticated: isAuthenticated,
      logout: logout,
      checkToken: checkToken
    };
  });
