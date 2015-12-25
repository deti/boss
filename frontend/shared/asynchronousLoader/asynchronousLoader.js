const dependencies = [];

export default angular.module('boss.asynchronousLoader', dependencies)
  .factory('asynchronousLoader', function ($q) {
    return {
      load: function (src) {
        var script,
          tags = document.getElementsByTagName('script'),
          alreadyAdded = !!_.find(tags, tag => tag.attributes.src && tag.attributes.src.value == src),
          deferred = $q.defer();

        if (alreadyAdded) {
          deferred.resolve();
        } else {
          script = document.createElement('script');
          script.type = 'text/javascript';
          script.src = src;
          script.onload = function () {
            deferred.resolve();
          };
          tags[0].parentNode.insertBefore(script, tags[0]);
        }

        return deferred.promise;
      }
    };
  });
