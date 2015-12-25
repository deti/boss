define([
  'angular',
  'jquery',
  'config',
  'lodash'
],
function (angular, $, config, _) {
  "use strict";

  var module = angular.module('grafana.routes');

  module.config(function($routeProvider) {
    $routeProvider
      .when('/dashboard/file/:jsonFile', {
        templateUrl: 'app/partials/dashboard.html',
        controller : 'DashFromFileProvider',
        reloadOnSearch: false,
      });
  });

  module.controller('DashFromFileProvider', function($scope, $rootScope, $http, $routeParams, alertSrv, $location, $window) {
    var search = $window.location.search, configName = null;

    var renderTemplate = function(json,params) {
      var _r;
      _.templateSettings = {interpolate : /\{\{(.+?)\}\}/g};
      var template = _.template(json);
      var rendered = template({ARGS:params});
      try {
        _r = angular.fromJson(rendered);
      } catch(e) {
        _r = false;
      }
      return _r;
    };

    var file_load = function(file) {
      return $http({
        url: "app/dashboards/"+file.replace(/\.(?!json)/,"/")+'?' + new Date().getTime(),
        method: "GET",
        transformResponse: function(response) {
          return renderTemplate(response,$routeParams);
        }
      }).then(function(result) {
        if(!result) {
          return false;
        }
        return result.data;
      },function() {
        alertSrv.set('Error',"Could not load <i>dashboards/"+file+"</i>. Please make sure it exists" ,'error');
        return false;
      });
    };
    if (search && _.contains(search, '?config=')) {
      configName = search.substring(search.indexOf('=') + 1);
    }
    if (configName) {
      console.log('load from specified config', configName);
      file_load(configName).then(function(result) {
        $scope.initDashboard(result, $scope);
      });
    } else {
      file_load($routeParams.jsonFile).then(function(result) {
        $scope.initDashboard(result, $scope);
      });
    }
  });

});
