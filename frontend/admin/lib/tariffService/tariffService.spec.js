import './tariffService';

describe('tariffService', function () {
  var $httpBackend,
    tariffService,
    tariffsGETResponse,
    tariffsPUTResponse,
    tariffsPOSTResponse,
    categories,
    result;

  tariffsGETResponse = {
    tariff_list: {
      items: [
        {
          'created': '2015-05-29T12:33:59+00:00',
          'deleted': null,
          'default': true,
          'services': [
            {
              'service': {
                'service_id': 'm1.medium',
                'mutable': false,
                'measure': {
                  'measure_id': 'hour',
                  'localized_name': {
                    'ru': 'час',
                    'en': 'hour'
                  },
                  'measure_type': 'time'
                },
                'description': {
                  'ru': 'Наилучшее решение для среднего бизнеса',
                  'en': 'The best solution for middle business'
                },
                'deleted': null,
                'category': {
                  'localized_name': {
                    'ru': 'Виртуальные машины',
                    'en': 'Virtual machine'
                  },
                  'category_id': 'vm'
                },
                'localized_name': {
                  'ru': 'Виртуальная машина m1.medium',
                  'en': 'Virtual machine m1.medium'
                }
              },
              'price': '40.00000000000000000000'
            }
          ],
          'description': 'новый 1',
          'mutable': false,
          'parent_id': null,
          'localized_name': {
            'ru': 'новый1',
            'en': 'new1'
          },
          'used': 29,
          'tariff_id': 1,
          'currency': 'USD'
        }
      ]
    }
  };

  result = [
    {
      'created': '2015-05-29T12:33:59+00:00',
      'deleted': null,
      'default': true,
      'services': [
        {
          'service': {
            'service_id': 'm1.medium',
            'mutable': false,
            'measure': {
              'measure_id': 'hour',
              'localized_name': {
                'ru': 'час',
                'en': 'hour'
              },
              'measure_type': 'time'
            },
            'description': {
              'ru': 'Наилучшее решение для среднего бизнеса',
              'en': 'The best solution for middle business'
            },
            'deleted': null,
            'category': {
              'localized_name': {
                'ru': 'Виртуальные машины',
                'en': 'Virtual machine'
              },
              'category_id': 'vm'
            },
            'localized_name': {
              'ru': 'Виртуальная машина m1.medium',
              'en': 'Virtual machine m1.medium'
            }
          },
          'price': '40.00000000000000000000'
        }
      ],
      'description': 'новый 1',
      'mutable': false,
      'parent_id': null,
      'localized_name': {
        'ru': 'новый1',
        'en': 'new1'
      },
      'used': 29,
      'tariff_id': 1,
      'currency': 'USD',
      'users': 29,
      'status': {localized_name: {en: 'Active', ru: 'Действующий'}, value: 'active'}
    }
  ];

  categories = [
    {
      'category_id': 'vm',
      'localized_name': {
        'ru': 'Виртуальные машины',
        'en': 'Virtual machine'
      },
      'services': [
        {
          'localized_name': {
            'ru': 'Виртуальная машина m1.small',
            'en': 'Virtual machine m1.small'
          },
          'description': {
            'ru': 'Cамая маленькая виртуалочка',
            'en': 'The smallest virtual machine'
          },
          'measure': {
            'measure_id': 'hour',
            'measure_type': 'time',
            'localized_name': {
              'ru': 'час',
              'en': 'hour'
            }
          },
          'service_id': 'm1.small',
          'price': '111.00000000000000000000',
          'selected': true
        }
      ]
    },
    {
      'category_id': 'storage',
      'localized_name': {
        'ru': 'Хранение данных',
        'en': 'Storage'
      },
      'services': [
        {
          'localized_name': {
            'ru': 'Диск',
            'en': 'Volume'
          },
          'description': {},
          'measure': {
            'measure_id': 'gigabyte*month',
            'measure_type': 'time_quant',
            'localized_name': {
              'ru': 'Гб*месяц',
              'en': 'Gb*month'
            }
          },
          'service_id': 'storage.volume',
          'price': 0,
          'selected': false
        }
      ]
    }
  ];

  tariffsPUTResponse = {
    'tariff_info': {
      'description': 'тест3',
      'deleted': null,
      'parent_id': null,
      'localized_name': {
        'ru': 'тест3',
        'en': 'test3'
      },
      'default': null,
      'tariff_id': 47,
      'services': [
        {
          'service': {
            'description': {
              'ru': 'Cамая маленькая виртуалочка',
              'en': 'The smallest virtual machine'
            },
            'deleted': null,
            'localized_name': {
              'ru': 'Виртуальная машина m1.small',
              'en': 'Virtual machine m1.small'
            },
            'service_id': 'm1.small',
            'measure': {
              'measure_id': 'hour',
              'measure_type': 'time',
              'localized_name': {
                'ru': 'час',
                'en': 'hour'
              }
            },
            'mutable': false,
            'category': {
              'category_id': 'vm',
              'localized_name': {
                'ru': 'Виртуальные машины',
                'en': 'Virtual machine'
              }
            }
          },
          'price': '111.00'
        }
      ],
      'mutable': true,
      'created': '2015-06-09T15:50:51+00:00',
      'currency': 'RUB'
    }
  };

  tariffsPOSTResponse = {
    'tariff_info': {
      'description': 'новый тариф',
      'deleted': null,
      'parent_id': null,
      'localized_name': {
        'ru': 'новый тариф',
        'en': 'new tariff'
      },
      'default': null,
      'tariff_id': 47,
      'services': [
        {
          'service': {
            'description': {
              'ru': 'Cамая маленькая виртуалочка',
              'en': 'The smallest virtual machine'
            },
            'deleted': null,
            'localized_name': {
              'ru': 'Виртуальная машина m1.small',
              'en': 'Virtual machine m1.small'
            },
            'service_id': 'm1.small',
            'measure': {
              'measure_id': 'hour',
              'measure_type': 'time',
              'localized_name': {
                'ru': 'час',
                'en': 'hour'
              }
            },
            'mutable': false,
            'category': {
              'category_id': 'vm',
              'localized_name': {
                'ru': 'Виртуальные машины',
                'en': 'Virtual machine'
              }
            }
          },
          'price': '111.00'
        }
      ],
      'mutable': true,
      'created': '2015-06-09T15:50:51+00:00',
      'currency': 'RUB'
    }
  };

  beforeEach(angular.mock.module('boss.tariffService'));

  beforeEach(inject(function (_$httpBackend_, _tariffService_) {
    $httpBackend = _$httpBackend_;
    tariffService = _tariffService_;
  }));

  it('getList should return tariffs list with additional fields', function (done) {
    $httpBackend.when('GET', '/tariff?show_used=true').respond(tariffsGETResponse);

    tariffService.getList()
      .then(function (res) {
        var plain = res.map(item => {
          return item.plain();
        });
        expect(plain).toEqual(result);
        done();
      });

    $httpBackend.flush();
  });

  it('updateTariff should form services array correctly and send PUT request to backend', function (done) {
    var tariff,
      expectedPayload;

    tariff = {
      tariff_id: 47
    };

    expectedPayload = {
      tariff: 47,
      currency: null,
      description: null,
      localized_name: null,
      services: [
        {
          service_id: 'm1.small',
          price: '111.00000000000000000000'
        }
      ]
    };

    $httpBackend.expectPUT('/tariff/47', expectedPayload).respond(tariffsPUTResponse);

    tariffService.updateTariff(tariff, categories)
      .finally(done);

    $httpBackend.flush();
  });

  it('createTariff should form services array correctly and send POST request to backend', function (done) {
    var tariff,
      expectedPayload;

    tariff = {
      localized_name: {
        ru: 'новый тариф',
        en: 'new tariff'
      },
      description: 'новый тариф',
      currency: 'RUB',
      parent_id: null
    };

    expectedPayload = {
      localized_name: {
        ru: 'новый тариф',
        en: 'new tariff'
      },
      description: 'новый тариф',
      currency: 'RUB',
      parent_id: null,
      services: [
        {
          service_id: 'm1.small',
          price: '111.00000000000000000000'
        }
      ]
    };

    $httpBackend.expectPOST('/tariff', expectedPayload).respond(tariffsPOSTResponse);

    tariffService.createTariff(tariff, categories)
      .finally(done);

    $httpBackend.flush();
  });
});
