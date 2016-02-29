import './customerService';

describe('customerService', function () {
  var $httpBackend,
    customerService;

  beforeEach(angular.mock.module('boss.customerService'));

  beforeEach(inject(function (_customerService_, _$httpBackend_, Restangular, $timeout) {
    $httpBackend = _$httpBackend_;
    customerService = _customerService_;
    Restangular.setOneBaseUrl = function (newBaseUrl) { // TODO: we should import it from run.js
      if (newBaseUrl) {
        var oldBaseUrl = Restangular.configuration.baseUrl;
        Restangular.setBaseUrl(newBaseUrl);
        $timeout(function () {
          Restangular.setBaseUrl(oldBaseUrl);
        });
      }
      return Restangular;
    };
  }));

  it('getSubscriptions should return subscriptions in format compatible with tags-input', function (done) {
    var response = {
      'subscribe': {
        'news': {
          'enable': true,
          'email': ['KMalysheva22@mfsa.ru']
        }
      }
    };
    var result = {
      'news': {
        'enable': true,
        'email': [{'text': 'KMalysheva22@mfsa.ru'}]
      }
    };
    $httpBackend.when('GET', '/customer/79/subscribe?customer=79').respond(response);

    customerService.getSubscriptions(79)
      .then(function (res) {
        expect(res).toEqual(result);
        done();
      });

    $httpBackend.flush();
  });

  it('updateSubscriptions should transform subscriptions in format compatible with backend', function (done) {
    var request = {
      customer: 79,
      subscribe: {
        news: {
          enable: true,
          email: ['KMalysheva22@mfsa.ru', 'test@test.com']
        }
      }
    };
    var subscriptions = {
      'news': {
        'enable': true,
        'email': [{'text': 'KMalysheva22@mfsa.ru'}, {'text': 'test@test.com'}]
      }
    };

    $httpBackend.expectPUT('/customer/79/subscribe', request).respond('');

    customerService.updateSubscriptions(79, subscriptions)
      .then(function () {
        done();
      });

    $httpBackend.flush();
  });

  it('should return correct customer list', function (done) {
    var res = {
      'customer_list': {
        'items': [{}],
        'total': 1,
        'per_page': 50,
        'page': 1
      }
    };

    $httpBackend.when('GET', '/customer').respond(res);

    customerService.getCustomers()
      .then(function (list) {
        expect(list.length).toBe(1);
        expect(list.total).toBe(1);
        expect(list.perPage).toBe(50);
        done();
      });

    $httpBackend.flush();
  });

  it('should load balance history', function (done) {
    $httpBackend.expectGET('/customer/1/balance/history').respond({account_history: 'empty'});

    customerService.getBalanceHistory(1, {})
      .then(function (history) {
        expect(history).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should load account history', function (done) {
    $httpBackend.expectGET('/customer/1/history').respond({history: 'empty'});

    customerService.getHistory(1, {})
      .then(function (history) {
        expect(history).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should load tariffInfo', function (done) {
    $httpBackend.expectGET('/customer/1/tariff').respond({tariff_info: 'empty'});

    customerService.getTariff(1)
      .then(function (tariff) {
        expect(tariff).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should load deferred changes', function (done) {
    $httpBackend.expectGET('/customer/1/deferred').respond({deferred: 'empty'});

    customerService.getDeferredChanges(1)
      .then(function (deferred) {
        expect(deferred).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should load customer quotas', function (done) {
    $httpBackend.expectGET('/customer/1/quota').respond({quota: 'empty'});

    customerService.quotas({customer_id: 1})
      .then(function (quotas) {
        expect(quotas).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to recreate cloud', function (done) {
    $httpBackend.expectPOST('/customer/1/recreate_tenant', {customer: 1}).respond('');

    customerService.recreateCloud({customer_id: 1})
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to confirm email', function (done) {
    $httpBackend.expectPUT('/customer/1/confirm_email').respond('');

    customerService.sendConfirmEmail(1)
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should update customer balance', function (done) {
    $httpBackend.expectPUT('/customer/1/balance', {amount: '2.00', comment: 'foo'}).respond({customer_info: 'empty'});

    customerService.updateBalance({customer_id: 1}, 2.000345, 'foo')
      .then(function (customer) {
        expect(customer).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to block customer', function (done) {
    $httpBackend.expectPUT('/customer/1/block', {blocked: true, message: 'foo'}).respond('');

    customerService.setBlocked({customer_id: 1}, true, 'foo')
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to reset customer password', function (done) {
    $httpBackend.expectDELETE('/lk_api/0/customer/password_reset?email=test@foo').respond('');

    customerService.resetPassword({customer_id: 1, email: 'test@foo'})
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to set customer to production mode', function (done) {
    $httpBackend.expectPOST('/customer/1/make_prod').respond({customer_info: 'empty'});

    customerService.makeProd({customer_id: 1})
      .then(function (customer) {
        expect(customer).toBe('empty');
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to apply quota template', function (done) {
    $httpBackend.expectPOST('/customer/1/quota', {template: 'foo'}).respond('');

    customerService.applyQuotaTemplate({customer_id: 1}, 'foo')
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to update quotas', function (done) {
    var quotas = [
      {limit_id: 'foo', value: 1},
      {limit_id: 'bar', value: 2}
    ];
    var request = {
      limits: {
        foo: 1,
        bar: 2
      }
    };
    $httpBackend.expectPUT('/customer/1/quota', request).respond('');

    customerService.updateQuotas({customer_id: 1}, quotas)
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should send request to create customer', function (done) {
    var customer = {
      contacts: {email: 'test@foo'},
      detailed_info: '',
      customer_mode: 'product',
      customer_type: 'entity',
      withdraw_period: 'day',
      locale: 'en-us'
    };
    var request = {
      email: 'test@foo',
      detailed_info: '',
      make_prod: true,
      customer_type: 'entity',
      withdraw_period: 'day',
      locale: 'en-us'
    };

    $httpBackend.expectPOST('/customer', request).respond('');

    customerService.createCustomer(customer)
      .then(function () {
        done();
      });
    $httpBackend.flush();
  });

  it('should update customer', function () {
    var customer = {
      save: function () {
      }
    };
    spyOn(customer, 'save');
    customerService.update(customer);

    expect(customer.save).toHaveBeenCalled();
  });

  it('should delete customer', function () {
    var customer = {
      remove: function () {
      }
    };
    spyOn(customer, 'remove');
    customerService.archive(customer);

    expect(customer.remove).toHaveBeenCalled();
  });
});
