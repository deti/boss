const dependencies = ['toaster'];

export default angular.module('skyline.dns.listCtrl', dependencies)
  .value('dnsActionsTpl', require('./cell.actions.partial.tpl.html'))
  .controller('OSDomainsCtrl', function OSDomainsCtrl($scope, domains, Designate, $filter, toaster, dnsActionsTpl) {
    $scope.actionsTplPath = dnsActionsTpl;
    $scope.domains = domains;

    $scope.deleteDomain = function (domain) {
      Designate.deleteDomain(domain)
        .then(rsp => {
          toaster.pop('success', $filter('translate')('Domain was successfully deleted'));
          var index = _.findIndex($scope.domains, domain);
          domains.splice(index, 1);
        })
        .catch(e => {
          toaster.pop('error', $filter('translate')('Error in the removal process'));
        });
    };

    $scope.columns = [
      {
        field: 'name',
        title: $filter('translate')('Name')
      },
      {
        field: 'records',
        title: $filter('translate')('Sub-domains'),
        value: function (item) {
          return item.records.toString();
        }
      },
      {
        field: 'email',
        title: $filter('translate')('email')
      }
    ];
  });
