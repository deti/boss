const dependencies = [
  'restangular', 'toaster', 'ui.router',
  require('./OSCredentials').default.name
];

export default angular.module('boss.openstackService.OSRestangular', dependencies)
  .factory('OSRestangular', function (Restangular, $state, toaster, $filter, OSCredentials, $rootScope, OS_CRED_UPDATE) {
    function errorInterceptor(response) {
      if (response.status === 401) {
        $state.reload(); // simply reload state and auth will get new token
        return false;
      } else if (response.status === 400 && response.data.badRequest) {
        toaster.pop('error', response.data.badRequest.message);
        return true;
      } else if (response.status === 403 && response.data.forbidden) {
        toaster.pop('error', response.data.forbidden.message);
        return true;
      } else if (response.status === 400 && response.data.message) {
        toaster.pop('error', response.data.message);
        return true;
      } else if (response.status === 409 && response.data.message) {
        toaster.pop('error', response.data.message);
      } else if (response.status >= 400 && response.status < 500) {
        return true;
        // toaster.pop('error', $filter('translate')('Error in the request processing'));
      }
      if (response.status >= 500) {
        console.log('Openstack error', response);
        toaster.pop('error', $filter('translate')('Server error'));
        return false;
      }
    }

    function getSingularForm(word) {
      if (_.endsWith(word, 's')) {
        return word.substring(0, word.length - 1);
      }
      return word;
    }

    function getBaseUrl(pattern) {
      return pattern.replace(/\{tenantId}/g, OSCredentials.tenantId);
    }
    /**
     * @param {string} baseUrlPattern
     * @param {{}=} config
     * @returns {*|IService}
     */
    function createOSRestangular(baseUrlPattern, config = {wrapPutRequest: true}) {
      var Rest = Restangular.withConfig(function (RestangularConfigurer) {
        RestangularConfigurer.configuration.errorInterceptors = []; // remove default error interceptor
        RestangularConfigurer.setBaseUrl(getBaseUrl(baseUrlPattern));
        RestangularConfigurer.setRequestSuffix('');
        RestangularConfigurer.addFullRequestInterceptor(function (element, operation, what, url, headers) {
          headers['X-Auth-Token'] = OSCredentials.token;
          return {
            headers: headers
          };
        });
        RestangularConfigurer.setOnElemRestangularized(function (data, some, route) {
          if (_.endsWith(route, 'detail') && data.fromServer) { // set correct url for requests to server/detail etc
            data.route = route.substring(0, route.length - 'detail'.length);
          }

          return data;
        });
      });
      $rootScope.$on(OS_CRED_UPDATE, function () {
        Rest.baseUrl = getBaseUrl(baseUrlPattern);
        Rest.setBaseUrl(Rest.baseUrl);
      });
      Rest.addResponseInterceptor((data, operation, what) => {
        if (operation === 'getList' || operation === 'get') {
          if (_.startsWith(what, 'os-')) { // handle os-keychain
            what = what.replace('os-', '');
            what = what.replace(/-/g, '_');
          }
          if (what.indexOf('/') !== -1) { // handle servers/detail flavors/detail, etc
            what = what.split('/')[0];
          }
        }
        if (operation === 'getList') {
          var keys = Object.keys(data);
          var newData = data[what];
          if (keys.length > 1) {
            keys.forEach(key => {
              if (key !== what) {
                newData[key] = data[key];
              }
            });
          }
          data = newData;
        }
        if (operation === 'get') {
          what = getSingularForm(what);
          if (data[what]) {
            data = data[what];
          }
        }
        return data;
      });
      Rest.addRequestInterceptor(function (elem, operation, what) {
        if (operation === 'remove') {
          return undefined;
        }
        if (config.wrapPutRequest && operation === 'put') {
          var elemName = getSingularForm(what);
          return {
            [elemName]: elem
          };
        }
        return elem;
      });

      Rest.setErrorInterceptor(errorInterceptor);

      return Rest;
    }

    return createOSRestangular;
  });
