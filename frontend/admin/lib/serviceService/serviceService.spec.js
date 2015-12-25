import './serviceService';

describe('serviceService', function () {
  var $httpBackend,
    tariffsResponse,
    serviceService,
    result;

  tariffsResponse = {
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
        },
        {
          'created': '2015-06-01T19:57:29+00:00',
          'deleted': '2015-06-03T16:24:05+00:00',
          'default': null,
          'services': [],
          'description': 'новый 6',
          'mutable': true,
          'parent_id': null,
          'localized_name': {
            'ru': 'новый6',
            'en': 'new6'
          },
          'used': 0,
          'tariff_id': 6,
          'currency': 'RUB'
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

  beforeEach(angular.mock.module('boss.serviceService'));

  beforeEach(inject(function (_$httpBackend_, _serviceService_) {
    $httpBackend = _$httpBackend_;
    serviceService = _serviceService_;
  }));

  it('should find tariffs with specified service', function (done) {
    var service = {
      service_id: 'm1.medium'
    };

    $httpBackend.when('GET', '/tariff?show_used=true').respond(tariffsResponse);

    serviceService.tariffsWithService(service)
      .then(function (res) {
        var plain = res.map(item => {
          return item.plain();
        });
        expect(plain).toEqual(result);
        done();
      });

    $httpBackend.flush();
  });
});
