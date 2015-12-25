const dependencies = [];
/**
 * @ngdoc filter
 * @name boss.table.filter:pickFilter
 *
 * @function
 * @description
 * Apply filters from configuration
 *
 * @param {String|*} filterConf Table data
 * @returns {*} Value after apply every filter
 *
 * @example
   <example module="app">
     <file name="app.html">
       <p>{{'SomeText' | pickFilter: 'lowercase'}}</p>
       <p>{{'SomeText' | pickFilter: ['lowercase', 'uppercase']}}</p>
     </file>
     <file name="script.js">
       angular.module('app', ['boss.table'])
         .controller('AppCtrl', function ($filter) {
           var pickFilter = $filter('pickFilter');
           pickFilter('someValue', 'lowercase'); // will apply lowercase filter to 'someValue'
           // also you can use array as a second param to apply multiple filters
           pickFilter('someValue', ['lowercase', 'uppercase']);
           // You can also use object notation to specify filter arguments
           pickFilter(new Date(), {name: 'date', args: ['yyyy']});
           // This is also works with arrays
           pickFilter(new Date(), [
             {name: 'date', args: ['yyyy']},
             {name: 'uppercase'}
           ]);
         });
     </file>
   </example>
 */
export default angular.module('boss.pickFilter', dependencies)
  .filter('pickFilter', function ($filter) {
    var applyFilter = function (filterConf, value) {
      var filter,
        filterArguments;
      if (typeof filterConf === 'string') {
        filter = $filter(filterConf);
        filterArguments = [value];
      } else if (_.isPlainObject(filterConf)) {
        filter = $filter(filterConf.name);
        filterArguments = _.clone(filterConf.args);
        filterArguments.unshift(value);
      }
      return filter.apply(this, filterArguments);
    };
    return function (value, filterConf) {
      if (filterConf) {
        if (!_.isArray(filterConf)) {
          return applyFilter(filterConf, value);
        }
        return filterConf.reduce((prevValue, currentValue) => {
          return applyFilter(currentValue, prevValue);
        }, value);
      }
      return value;
    };
  });
