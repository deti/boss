import './bsMatch';

describe('Test match', function () {
  var $scope, form;

  beforeEach(angular.mock.module('boss.match'));
  beforeEach(inject(function ($compile, $rootScope) {
    $scope = $rootScope;
    var element = angular.element(
      '<form name="form">' +
      '<input type="password" name="password" ng-model="password" />' +
      '<input type="password" name="passwordAgain" ng-model="passwordAgain" bs-match="password" />' +
      '</form>'
    );
    $compile(element)($scope);
    form = $scope.form;
  }));

  it('generate fail password (without small letters)', function () {
    var string = 'testPass';
    form.password.$setViewValue(string);
    form.passwordAgain.$setViewValue(string);
    expect(form.passwordAgain.$valid).toBe(true);
    form.passwordAgain.$setViewValue('mismatchPass');
    expect(form.passwordAgain.$valid).toBe(false);
  });
});
