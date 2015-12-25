const dependencies = [];
/**
 * @ngdoc directive
 * @name boss.shared.directive:bsDynamicName
 * @restrict A
 * @element ANY
 *
 * @description
 * Add form control with dynamic name to form controller.
 *
 * @example
   <example module="Example">
     <file name="file.html">
       <form name="SomeForm" ng-controller="AppCtrl">
         <input name="{{otherControl}}" type="text" ng-model="model1">
         <pre>{{SomeForm.otherControl | json}}</pre>
         <input name="{{controlName}}" type="text" ng-model="model2" bs-dynamic-name>
         <pre>{{SomeForm.superControl | json}}</pre>
       </form>
     </file>
     <file name="controller.js">
       angular.module('Example', [])
         .controller('AppCtrl', function ($scope) {
           $scope.controlName = 'superControl';
           $scope.otherName = 'otherControl';
         });
     </file>
   </example>
 */
export default angular.module('boss.dynamicName', dependencies)
  .directive('bsDynamicName', function () {
    return {
      restrict: 'A',
      require: ['ngModel', '^form'],
      link: function (scope, element, attrs, [modelCtrl, formCtrl]) {
        modelCtrl.$name = scope.$eval(attrs.name) || attrs.name;
        formCtrl.$addControl(modelCtrl);
      }
    };
  });
