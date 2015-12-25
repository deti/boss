const dependencies = [];
const config = require('../../config');
import constants from '../../../shared/constants/constants';
import defaultLocalConfig from './defaultLocalConfig';

export const CONST = angular.extend({
  local: angular.extend({}, window.CONFIG || defaultLocalConfig),
  constants: constants,
  defaultLocale: 'en-US',
  api: '/lk_api/0/',
  relativePath: 'lk'
}, config);

export default angular.module('boss.const', dependencies)
  .constant('CONST', CONST);
