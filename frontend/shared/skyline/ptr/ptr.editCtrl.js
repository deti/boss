const dependencies = [
  'toaster',
  require('../../openstackService/DesignateV2').default.name
];

export default angular.module('skyline.ptr.editCtrl', dependencies)
  .controller('PTREditCtrl', function ($filter, $state, $q, toaster, DesignateV2, zone, recordsets) {
    var record = _.find(recordsets, {type: 'PTR'});
    this.record = record;
    this.zone = zone;
    this.ip = DesignateV2.ipFromPtrName(zone.name);

    this.updateZone = function (form) {
      if (!_.endsWith(this.record.records[0], '.')) {
        this.record.records[0] += '.';
      }
      var promises = [
        zone.patch({email: zone.email}),
        record.save()
      ];
      $q.all(promises)
        .then(r => {
          toaster.pop('success', $filter('translate')('Record was succesfully updated'));
          $state.go('openstack.ptr', {}, {reload: true});
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Failed to save record'));
          form.$resetSubmittingState();
        });
    };
  });
