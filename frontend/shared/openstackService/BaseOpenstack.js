const dependencies = [
  require('./OSCredentials').default.name,
  require('./OSRestangular').default.name,
  require('../urlParser/urlParser').default.name
];

export default angular.module('boss.openstackService.BaseOpenstack', dependencies)
  .factory('BaseOpenstack', function ($document, $http, OSRestangular, $q, URLParser, OSCredentials) {
    /**
     * @property {object} services
     * @property {Nova} services.Nova
     * @property {Glance} services.Glance
     * @property {Cinder} services.Cinder
     * @property {Neutron} services.Neutron
     * @property {Mistral} services.Mistral
     * @property {Neutron} services.Neutron
     * @property {Designate} services.Designate
     * @property {DesignateV2} services.DesignateV2
     */
    class BaseOpenstack {
      constructor(baseUrlPattern, restangularConfig) {
        this.Restangular = OSRestangular(baseUrlPattern, restangularConfig);
      }

      /**
       * @param {string} url
       * @returns {HttpPromise}
       */
      load(url) {
        return $http.get(url, {
          headers: {
            'X-Auth-Token': OSCredentials.token
          }
        }).then(response => {
          return response.data;
        });
      }

      static getNextMarker(obj, entityName) {
        if (!obj[`${entityName}_links`] && !obj.next) {
          return false;
        }
        var href;
        if (obj.next) {
          href = obj.next;
        } else {
          var links = obj[`${entityName}_links`];
          var next = _.find(links, l => l.rel === 'next');
          if (next === undefined) {
            return false;
          }
          href = next.href;
        }
        var urlParser = new URLParser(href);
        var marker = urlParser.searchParam('marker');
        if (!marker) {
          return false;
        }
        return marker;
      }

      /**
       * Loads full list of entities, paginated like http://docs.openstack.org/developer/nova/v2/paginated_collections.html
       * @param {restangular.ICollection} route Restangular route, that can accept getList fn
       * @param {string} entityName entity name, used to get property name for links array
       * @param {Object} [params = {}] additional params to be passed to getList
       * @param {number|null} [limit = null] Items per page
       * @param {string|null} [prevMarker = null] ID of last item in previous list
       * @returns {deferred.promise|{then, catch, finally}} Promise, that will resolve with full loaded list
       */
      loadFullList(route, entityName, params = {}, limit = null, prevMarker = null) {
        var deferred = $q.defer();
        var queryParams = angular.extend({}, params, {
          marker: prevMarker,
          limit
        });
        route.getList(queryParams)
          .then(list => {
            var marker = BaseOpenstack.getNextMarker(list, entityName);
            if (!marker || list.length === 0) {
              deferred.resolve(list);
            } else {
              if (!limit) {
                limit = list.length;
              }
              this.loadFullList(route, entityName, params, limit, marker)
                .then(newList => {
                  list = list.concat(newList);
                  deferred.resolve(list);
                })
                .catch(deferred.reject);
            }
          })
          .catch(deferred.reject);

        return deferred.promise;
      }
    }

    return BaseOpenstack;
  });
