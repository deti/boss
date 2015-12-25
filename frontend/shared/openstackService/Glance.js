const dependencies = [
  require('./OSCredentials').default.name,
  require('./BaseOpenstack').default.name
];

export default angular.module('boss.openstackService.Glance', dependencies)
  .factory('Glance', function (BaseOpenstack, $http, IMAGE_STATUS, OSCredentials) {
    class Glance extends BaseOpenstack {
      constructor() {
        super('/glance/v2/');

        this.Restangular.extendModel('images', function (model) {
          if (model.owner) {
            model.own = model.owner === OSCredentials.tenantId;
          }
          if (model.status && typeof model.status === 'string') {
            if (typeof IMAGE_STATUS[model.status] !== 'undefined') {
              model.status = angular.copy(IMAGE_STATUS[model.status]);
            } else {
              console.log('unknown image status', model.status);
            }
          }
          return model;
        });
      }

      images(params = {}) {
        return this.loadFullList(this.Restangular.all('images'), 'images', params);
      }

      image(id) {
        return this.Restangular.one('images', id).get();
      }

      createImage(image) {
        return $http.post('/glance/v1/images', undefined, {
          headers: {
            'X-Auth-Token': OSCredentials.token,
            'x-image-meta-disk-format': 'iso',
            'x-glance-api-copy-from': image.url,
            'x-image-meta-name': image.name
          }
        });
      }
    }

    return new Glance();
  })
  .factory('IMAGE_STATUS', function ($filter) {
    return {
      active: {title: $filter('translate')('Available'), value: 'active'},
      queued: {title: $filter('translate')('Queued'), value: 'queued', progress: true},
      saving: {title: $filter('translate')('Saving'), value: 'saving', progress: true},
      killed: {title: $filter('translate')('Error'), value: 'killed'},
      deleted: {title: $filter('translate')('Removed'), value: 'deleted', progress: true},
      pending_delete: {title: $filter('translate')('Removed'), value: 'pending_delete', progress: true}
    };
  });
