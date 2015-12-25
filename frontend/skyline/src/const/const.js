const dependencies = [];
const config = require('../../config');
import constants from '../../../shared/constants/constants';

export const CONST = angular.extend({
  local: {
    'google_analytics': {'lk': 'UA-62743660-3', 'admin': 'UA-62743660-4'}
  },
  constants: constants,
  relativePath: 'skyline',
  defaultLocale: 'ru-RU',
  floating_ips: false,
  dns: false,
  red_stars: true,
  manual_disk_size: false
}, config);

export default angular.module('boss.const', dependencies)
  .constant('CONST', CONST);
