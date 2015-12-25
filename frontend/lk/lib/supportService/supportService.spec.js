describe('supportService', function () {
  var supportService, $httpBackend;

  beforeEach(module('boss.supportService'));

  beforeEach(inject(function (_supportService_, _$httpBackend_) {
    supportService = _supportService_;
    $httpBackend = _$httpBackend_;
  }));

  it('should send message to support', function () {
    var message = {
      subject: 'foo',
      body: 'bar',
      copies: [{text: 'test@foo'}]
    };
    var request = {
      subject: 'foo',
      body: 'bar',
      copy: ['test@foo']
    };
    $httpBackend.expectPOST('/customer/support', request).respond('');
    supportService.sendMessage(message);
    $httpBackend.flush();
  });
});
