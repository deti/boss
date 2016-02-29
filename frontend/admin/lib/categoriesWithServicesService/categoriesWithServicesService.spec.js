import './categoriesWithServicesService';

describe('categoriesWithServicesService', function () {
  var $httpBackend,
    servicesResponse,
    categoriesResponse,
    categoriesWithServices;

  var service1 = {
    'measure': {
      'measure_id': 'hour',
      'localized_name': {
        'ru': 'час',
        'en': 'hour'
      },
      'measure_type': 'time'
    },
    'category': {
      'localized_name': {
        'ru': 'Виртуальные машины',
        'en': 'Virtual machine'
      },
      'category_id': 'vm'
    },
    'mutable': false,
    'service_id': 'vm.Micro',
    'description': {},
    'deleted': null,
    'localized_name': {
      'ru': 'Виртуальная машина Micro',
      'en': 'Virtual machine Micro'
    }
  };
  var service2 = {
    'measure': {
      'measure_id': 'hour',
      'localized_name': {
        'ru': 'час',
        'en': 'hour'
      },
      'measure_type': 'time'
    },
    'category': {
      'localized_name': {
        'ru': 'Виртуальные машины',
        'en': 'Virtual machine'
      },
      'category_id': 'vm'
    },
    'mutable': false,
    'service_id': 'vm.medium',
    'description': {},
    'deleted': null,
    'localized_name': {
      'ru': 'Виртуальная машина Medium',
      'en': 'Virtual machine Medium'
    }
  };
  var service3 = {
    'measure': {
      'measure_id': 'gigabyte*month',
      'localized_name': {
        'ru': 'Гб*месяц',
        'en': 'Gb*month'
      },
      'measure_type': 'time_quant'
    },
    'category': {
      'localized_name': {
        'ru': 'Хранение данных',
        'en': 'Storage'
      },
      'category_id': 'storage'
    },
    'mutable': false,
    'service_id': 'storage.volume',
    'description': {},
    'deleted': null,
    'localized_name': {
      'ru': 'Диск',
      'en': 'Volume'
    }
  };

  servicesResponse = {
    'service_list': {
      per_page: 50, page: 1,
      items: [
        service1, service2, service3
      ]
    }
  };

  categoriesResponse = {
    'category_list': [
      {
        'category_id': 'vm',
        'localized_name': {
          'ru': 'Виртуальные машины',
          'en': 'Virtual machine'
        }
      },
      {
        'category_id': 'storage',
        'localized_name': {
          'ru': 'Хранение данных',
          'en': 'Storage'
        }
      }
    ]
  };

  categoriesWithServices = [
    {
      'category_id': 'vm',
      'localized_name': {
        'ru': 'Виртуальные машины',
        'en': 'Virtual machine'
      },
      'services': [
        _.extend({}, service1, {price: 0, selected: false, need_changing: null}),
        _.extend({}, service2, {price: 0, selected: false, need_changing: null})
      ]
    },
    {
      'category_id': 'storage',
      'localized_name': {
        'ru': 'Хранение данных',
        'en': 'Storage'
      },
      'services': [
        _.extend({}, service3, {price: 0, selected: false, need_changing: null})
      ]
    }
  ];

  beforeEach(angular.mock.module('boss.categoriesWithServicesService'));

  it('should pass a dummy test', inject(function (categoriesWithServicesService) {
    expect(categoriesWithServicesService).toBeTruthy();
  }));

  describe('get', function () {
    beforeEach(inject(function ($injector) {
      $httpBackend = $injector.get('$httpBackend');
      $httpBackend.when('GET', '/category').respond(categoriesResponse);
    }));

    it('should merge services from backend and categories from backend', function (done) {
      inject(function (categoriesWithServicesService, $injector) {
        var resultCategories = [];
        $httpBackend = $injector.get('$httpBackend');
        $httpBackend.when('GET', '/service').respond(servicesResponse);
        categoriesWithServicesService.get()
          .then(function (res) {
            resultCategories = res;
            expect(resultCategories).toEqual(categoriesWithServices);
            done();
          });
        $httpBackend.flush();
      });
    });
  });

  describe('mergeTariffServices', function () {
    var tariffServices,
      categoriesResult;

    tariffServices = [
      {
        'price': '300.000000',
        'service': service1
      },
      {
        'price': '250.000000',
        'service': service3
      }
    ];

    categoriesResult = [
      {
        'localized_name': {
          'ru': 'Виртуальные машины',
          'en': 'Virtual machine'
        },
        'category_id': 'vm',
        'services': [
          _.extend(service1, {price: '300.000000', selected: true, need_changing: undefined}),
          _.extend(service2, {price: 0, selected: false, need_changing: null})
        ]
      },
      {
        'localized_name': {
          'ru': 'Хранение данных',
          'en': 'Storage'
        },
        'category_id': 'storage',
        'services': [
          _.extend(service3, {price: '250.000000', selected: true, need_changing: undefined})
        ]
      }
    ];

    it('should mark tariff services in categories with services list', inject(function (categoriesWithServicesService) {
      var res = categoriesWithServicesService.mergeTariffServices(tariffServices, categoriesWithServices);
      expect(res).toEqual(categoriesResult);
    }));
  });
});
