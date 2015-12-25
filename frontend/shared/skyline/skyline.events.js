export default angular.module('skyline.events', [])
  .constant('SKYLINE_EVENTS', {
    SERVER_CREATED: 'skyline.server.created',
    SERVER_UPDATED: 'skyline.server.updated',
    SERVER_DELETED: 'skyline.server.deleted',

    VOLUME_CREATED: 'skyline.volume.created',
    VOLUME_DELETED: 'skyline.volume.deleted',
    VOLUME_EXTENDED: 'skyline.volume.extended',

    IP_CREATED: 'skyline.ip.created',
    IP_DELETED: 'skyline.ip.deleted'
  });
