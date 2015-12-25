const dependencies = ['angular-loading-bar'];

export default angular.module('boss.pollService', dependencies)
  .factory('pollService', function ($interval, $q, $timeout, cfpLoadingBar) {
    /**
     * Task function description
     * @callback pollServiceTaskFn
     * @returns {Promise}
     */

    /**
     * Handler function description
     * @callback pollServiceHandlerFn
     * @params {object} rsp
     */

    /**
     * Runs task repeatedly, with some time delay and either copy function response to destObj or call handler function
     * @param {pollServiceTaskFn} task Function, that will be called every time when timeout elapsed. Should return
     * a promise that will resolve to an object
     * @param {Object} destObj Object reference to copy task result
     * @param {number|function=} timeout Timeout in millisecond or function, that return timeout between each task execution
     * @param {number=} limit Limit of task execution. Task will executes infinitely if limit = 0
     * @param {pollServiceHandlerFn=} handler Function to call on every task execution
     * @returns {Promise}
     */
    function startPolling(task, destObj, timeout = 60 * 1000, limit = 0, handler = null) {
      var deferred = $q.defer();
      var promise = deferred.promise;

      promise.n = 0;
      promise.canceled = false;
      promise.timeoutPromise = null;
      promise.stop = function () {
        stopPolling(promise);
      };

      var fn = function () {
        cfpLoadingBar.set(1); // disable loading bar for polling requests
        task()
          .then(rsp => {
            cfpLoadingBar.set(0);
            if (handler) {
              handler(rsp);
            } else {
              if (!_.isEqual(rsp, destObj)) {
                angular.copy(rsp, destObj);
              }
            }
            promise.n++;
            if (limit && promise.n >= limit) {
              deferred.reject('limit reached');
              return;
            }
            if (promise.canceled) {
              deferred.reject('canceled');
              return;
            }
            promise.timeoutPromise = $timeout(fn, _.isFunction(timeout) ? timeout(promise.n) : timeout);
          })
          .catch(err => {
            deferred.reject(err);
            cfpLoadingBar.set(0);
            stopPolling(promise);
          });
      };
      fn();
      return promise;
    }

    function stopPolling(p) {
      p.canceled = true;
      $timeout.cancel(p.timeoutPromise);
    }

    // timing function https://goo.gl/zwI5LC
    function sigmoidTiming(x) {
      let steepness = 0.2;
      let maxValue = 10;
      let midPoint = 12;
      return (maxValue / (Math.pow(Math.E, steepness * (-x + midPoint)) + 1)) * 1000;
    }

    /**
     * Execute task repeatedly until stopFn will return true or limit will be reached
     * @param {pollServiceTaskFn} task
     * @param {pollServiceHandlerFn} stopFn
     * @param {number=} limit
     * @returns {Promise}
     */
    function asyncTask(task, stopFn, limit = 0) {
      var deferred = $q.defer();
      var promise = startPolling(task, {}, sigmoidTiming, limit, function (rsp) {
        if (stopFn(rsp)) {
          promise.stop();
          deferred.resolve(rsp);
        }
      });
      promise.catch(err => deferred.reject(err));
      deferred.promise.stop = promise.stop;
      return deferred.promise;
    }

    return {
      startPolling,
      stopPolling: stopPolling,
      sigmoidTiming,
      asyncTask
    };
  });
