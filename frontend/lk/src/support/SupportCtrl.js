const dependencies = [
  'ui.router',
  'toaster',
  'boss.const',
  require('../../lib/supportService/supportService').default.name
];

export default angular.module('boss.lk.SupportCtrl', dependencies)
  .controller('SupportCtrl', function SupportCtrl($scope, $state, $filter, userInfo, supportService, toaster, CONST) {
    $scope.user = _.clone(userInfo);
    $scope.headingItemsCount = 0;
    $scope.message = {};
    $scope.subjects = [
      $filter('translate')('Billing issues'),
      $filter('translate')('Technical issues')
    ];

    var cards = [];
    cards.push(CONST.local.provider_info.support_phone, CONST.local.provider_info.site_url_ui, CONST.local.provider_info.support_email);
    cards.forEach(value => {
      if (value !== null) {
        $scope.headingItemsCount += 1;
      }
    });

    $scope.send = function () {
      supportService.sendMessage($scope.message)
        .then(function (rsp) {
          toaster.pop('success', $filter('translate')('Message is sent'));
          $state.reload();
        }, function (err) {
          if (err.data && err.data.localized_message) {
            toaster.pop('error', err.data.localized_message);
          } else {
            toaster.pop('error', $filter('translate')('Server error'));
          }
        });
    };
  });
