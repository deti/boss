import cronToText from 'cron-to-text';

const dependencies = [
  require('../appLocale/appLocale').default.name
];

const ruLocale = JSON.parse(require('./cron_ru.i18n.json'));

export default angular.module('boss.cronToTextFilter', dependencies)
  .filter('cronToText', function (appLocale) {
    return function (input, sixth = false) {
      return cronToText(input, sixth, appLocale.getLang(true) === 'ru' ? ruLocale : undefined);
    };
  });
