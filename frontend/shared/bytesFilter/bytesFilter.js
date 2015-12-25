const dependencies = [];

export default angular.module('boss.bytesFilter', dependencies)
  .filter('bytes', function () {
    return function (bytes, baseUnit = 'bytes', precision = 0) {
      if (isNaN(parseFloat(bytes)) || !isFinite(bytes)) {
        return '-';
      }

      var units = ['bytes', 'kB', 'MB', 'GB', 'TB'],
        unitsBytes = [1, 1024, Math.pow(1024, 2), Math.pow(1024, 3), Math.pow(1024, 4), Math.pow(1024, 5)];
      baseUnit = _.find(units, u => {
        return baseUnit.toLowerCase() === u.toLowerCase();
      });
      if (!baseUnit) {
        baseUnit = 'bytes';
      }
      if (bytes === 0) {
        return `${bytes} ${baseUnit}`;
      }
      bytes = bytes * unitsBytes[units.indexOf(baseUnit)];
      var number = Math.floor(Math.log(bytes) / Math.log(1024));
      return (bytes / Math.pow(1024, Math.floor(number))).toFixed(precision) + ' ' + units[number];
    };
  });
