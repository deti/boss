import './appLocale';

describe('appLocale', function () {
  var appLocale, $translate, tmhDynamicLocale, ipCookie, $rootScope, CONST, $window, $timeout;

  ipCookie = function () {
  };

  beforeEach(function () {
    angular.mock.module('boss.appLocale', function ($provide) {
      $provide.factory('$translate', function ($q) {
        function translate() {
          return $q.when(true);
        }

        translate.use = function () {
          return 'en-US';
        };
        translate.storage = function () {
          return false;
        };
        translate.storageKey = function () {
          return '';
        };
        translate.preferredLanguage = function () {
          return 'en-US';
        };
        return translate;
      });
    })
  });

  beforeEach(inject(function (_appLocale_, _$translate_, _tmhDynamicLocale_, _ipCookie_, _$rootScope_, _CONST_, _$window_, _$timeout_) {
    appLocale = _appLocale_;
    $translate = _$translate_;
    tmhDynamicLocale = _tmhDynamicLocale_;
    ipCookie = _ipCookie_;
    $rootScope = _$rootScope_;
    CONST = _CONST_;
    $window = _$window_;
    $timeout = _$timeout_;
  }));

  beforeEach(function () {
    spyOn(tmhDynamicLocale, 'set');
  });

  describe('locale not loaded', function () {
    it('should return default locale when locale not loaded', function () {
      CONST.fe.defaultLocale = 'test';
      expect(appLocale.getLocale(true)).toBe('test');
    });
    it('should load locale', function (done) {
      appLocale.getLocale()
        .then(function (locale) {
          expect(locale).toBe('en-US');
          done();
        });
      $rootScope.$digest();
    });
  });

  describe('locale loaded', function () {
    beforeEach(function (done) {
      appLocale.load()
        .then(function () {
          done();
        });
      $rootScope.$apply();
    });

    it('Should set horizon language', function () {
      expect(appLocale.getLocale(true)).toBe('en-US');
      expect(ipCookie('horizon_language')).toBe('en');
    });

    it('should get locale with promise', function (done) {
      appLocale.getLocale()
        .then(function (locale) {
          expect(locale).toBe('en-US');
          done();
        });
    });

    it('should return lang', function () {
      expect(appLocale.getLang(true)).toBe('en');
    });

    it('should get lang with promise', function (done) {
      appLocale.getLang()
        .then(function (lang) {
          expect(lang).toBe('en');
          done();
        });
    });

    it('should get locale in backend format', function () {
      expect(appLocale.getBackendLocale(true)).toBe('en_us');
    });
    it('should get locale in backend format with promise', function () {
      appLocale.getBackendLocale()
        .then(function (locale) {
          expect(locale).toBe('en_us');
          done();
        });
    });

    it('should set locale and reload page', function () {
      spyOn($window.location, 'reload');
      spyOn($translate, 'use');
      appLocale.setLocale('ru-RU');
      expect(ipCookie('horizon_language')).toBe('ru');
      expect($translate.use).toHaveBeenCalledWith('ru-RU');
      //$timeout.flush(); // TODO: flush causes $digest already in progress error
      //expect($window.location.reload).toHaveBeenCalled();
    });

    it('should set locale based on language', function () {
      spyOn($window.location, 'reload');
      spyOn($translate, 'use');
      appLocale.setLang('ru');
      expect(ipCookie('horizon_language')).toBe('ru');
      expect($translate.use).toHaveBeenCalledWith('ru-RU');
    });
  });
});
