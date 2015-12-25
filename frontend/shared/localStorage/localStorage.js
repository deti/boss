const dependencies = [];

export default angular.module('boss.localStorage', dependencies)
  .factory('localStorage', function () {
    return {
      getItem: function (item, defaultValue = undefined) {
        var lsItem = localStorage.getItem(item);
        if (lsItem === null) {
          if (defaultValue !== undefined) {
            this.setItem(item, defaultValue);
          }
          return defaultValue;
        }
        try {
          return JSON.parse(lsItem);
        } catch (error) {
          return lsItem;
        }
      },
      setItem: function (item, value) {
        if (_.isObject(value)) {
          value = JSON.stringify(value);
        }
        localStorage.setItem(item, value);
      }
    };
  });
