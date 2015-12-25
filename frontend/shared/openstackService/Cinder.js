const dependencies = [
  require('./BaseOpenstack').default.name,
  require('./VolumeModel').default.name,
  require('./SnapshotModel').default.name
];

export default angular.module('boss.openstackService.Cinder', dependencies)
  .factory('Cinder', function (BaseOpenstack, $q, VolumeModel, SnapshotModel, $injector) {
    var Nova = false; // Nova and Cinder are in circular dependency. So we will init it later TODO: remove circular dependency
    function initNova() {
      if (!Nova) {
        Nova = $injector.get('Nova');
      }
    }
    class Cinder extends BaseOpenstack {
      constructor() {
        super('/cinder/v2/{tenantId}/');
        this.Restangular.extendModel('volumes/detail', VolumeModel);
        this.Restangular.extendModel('volumes', VolumeModel);
        this.Restangular.extendModel('snapshots', SnapshotModel);
      }

      volumes(simple = false, params = {}) {
        var route = simple ? 'volumes' : 'volumes/detail';
        return this.loadFullList(this.Restangular.all(route), 'volumes', params)
          .then(volumes => {
            if (simple) {
              return volumes;
            }
            var promises = volumes.map(volume => {
              return this.volumeLinkedServer(volume);
            });

            return $q.all(promises)
              .then(() => volumes);
          });
      }

      availableVolumes() {
        return this.volumes()
          .then(volumes => {
            return _.filter(volumes, volume => volume.attachments.length === 0);
          });
      }

      volume(id) {
        return this.Restangular.one('volumes', id).get();
      }

      volumeLinkedServer(volume) {
        initNova();
        if (volume.attachments.length) {
          return Nova.server(volume.attachments[0].server_id)
            .then(server => {
              volume.server = server;
              return volume;
            });
        } else {
          volume.server = undefined;
        }
        return $q.when(volume);
      }

      createVolume(volume) {
        return this.Restangular.all('volumes').post({volume});
      }

      extendVolume(volume) {
        return this.Restangular.one('volumes', volume.id).one('action').post('', {'os-extend': {'new_size': volume.newSize}});
      }

      snapshots(params) {
        return this.loadFullList(this.Restangular.all('snapshots'), 'snapshots', params);
      }

      snapshotsWithLinkedServers() {
        return this.snapshots()
          .then(snapshots => {
            var promises = snapshots.map(s => this.snapshotLinkedServer(s));
            return $q.all(promises);
          });
      }

      snapshotLinkedServer(snapshot) {
        return Nova.server(snapshot.instanceId)
          .then(server => {
            snapshot.server = server;
            return snapshot;
          })
          .catch(e => {
            snapshot.server = false;
            return snapshot;
          });
      }

      snapshot(id) {
        return this.Restangular.one('snapshots', id).get();
      }

      limits() {
        return this.Restangular.one('limits').get()
          .then(r => {
            return r.limits;
          });
      }
    }

    return new Cinder();
  });
