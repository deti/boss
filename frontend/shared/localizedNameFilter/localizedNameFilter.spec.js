import './localizedNameFilter'
describe('LocalizedNameFilter', function () {
  var localizedNameFilter,
    appLocale;
  beforeEach(function () {
    angular.mock.module('boss.localizedNameFilter');
  });
  beforeEach(inject(function ($filter, _appLocale_) {
    localizedNameFilter = $filter('localizedName');
    appLocale = _appLocale_;
  }));

  it('should return throw exception for objects without localized_name field', function () {
    var obj = {};
    expect(function () {
      localizedNameFilter(obj);
    }).toThrow();
  });

  it('should return correct translation', function () {
    var obj = {
      'localized_name': {
        'ru': 'тестовое имя',
        'en': 'test name'
      }
    };
    spyOn(appLocale, 'defaultLang').and.returnValue('en');
    spyOn(appLocale, 'getLang').and.returnValues('ru', 'en');
    expect(localizedNameFilter(obj)).toEqual('тестовое имя');
    expect(localizedNameFilter(obj)).toEqual('test name');
  });

  it('should return field with default lang if correct translation not exist', function () {
    var obj = {
      'localized_name': {
        'en': 'test name'
      }
    };
    spyOn(appLocale, 'getLang').and.returnValue('ru');
    spyOn(appLocale, 'defaultLang').and.returnValue('en');
    expect(localizedNameFilter(obj)).toEqual('test name');
  });

  it('should return empty string when there is no translation in object', function () {
    var obj = {
      'localized_name': {
      }
    };
    spyOn(appLocale, 'getLang').and.returnValue('ru');
    spyOn(appLocale, 'defaultLang').and.returnValue('en');
    expect(localizedNameFilter(obj)).toBe('');
  });

  it('should allow to use other field for localization', function () {
    var obj = {
      'localized_description': {
        'ru': 'тестовое имя',
        'en': 'test name'
      }
    };
    spyOn(appLocale, 'defaultLang').and.returnValue('en');
    spyOn(appLocale, 'getLang').and.returnValues('ru', 'en');
    expect(localizedNameFilter(obj, 'localized_description')).toEqual('тестовое имя');
    expect(localizedNameFilter(obj, 'localized_description')).toEqual('test name');
  });
});
