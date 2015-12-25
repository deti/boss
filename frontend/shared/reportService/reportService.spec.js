import './reportService';

describe('reportService', function () {
  var reportService,
    $httpBackend,
    fileSaver,
    $timeout;
  var startDate = new Date('December 17, 2015 03:24:00');
  var endDate = new Date('December 18, 2015 03:24:00');
  beforeEach(angular.mock.module('boss.reportService'));

  beforeEach(inject(function (_reportService_, _$httpBackend_, _$timeout_, _fileSaver_) {
    reportService = _reportService_;
    $httpBackend = _$httpBackend_;
    $timeout = _$timeout_;
    fileSaver = _fileSaver_;
  }));

  it('Should pass dummy test', function () {
    expect(reportService).toBeTruthy();
  });

  it('Should get report json', function (done) {
    $httpBackend.when('POST', '/url').respond({status: 'completed', info: 'test'});

    reportService.getJSON('/url', startDate, endDate)
      .then(function (response) {
        expect(response).toEqual({status: 'completed', info: 'test'});
        done();
      });
    $httpBackend.flush();
    $timeout.flush();
  });

  it('Should call backend until get correct response', function (done) {
    var res = {status: 'in progress', info: 'test'};
    $httpBackend.when('POST', '/url').respond(res);

    reportService.getJSON('/url', startDate, endDate)
      .then(function (response) {
        expect(response).toEqual({status: 'completed', info: 'test'});
        done();
      });
    $httpBackend.flush();
    $timeout.flush();
    res.status = 'completed';
    $httpBackend.flush();
    $timeout.flush();
  });

  it('Should reject promise if backend respond with error status', function (done) {
    var res = {status: 'error', info: 'test'};
    $httpBackend.when('POST', '/url').respond(res);

    reportService.getJSON('/url', startDate, endDate)
      .catch(function (response) {
        expect(response).toEqual('error');
        done();
      });
    $httpBackend.flush();
    $timeout.flush();
  });


  it('Should return error if can not get report from server for 1 minute', function (done) {
    $httpBackend.when('POST', '/url').respond({status: 'in progress'});

    reportService.getJSON('/url', startDate, endDate)
      .catch(function (e) {
        expect(e).toBe('error');
        done();
      });

    for (var i = 0; i < 50; i++) {
      $timeout.flush();
      $httpBackend.flush();
    }
  });

  it('Should format date correctly', function (done) {
    $httpBackend.expectPOST('/url', {
      start: '2015-12-17T00',
      finish: '2015-12-18T00',
      report_format: 'json',
      report_type: 'simple'
    }).respond({status: 'completed'});

    var startDate = new Date('December 17, 2015 03:24:00');
    var endDate = new Date('December 18, 2015 03:24:00');

    reportService.getJSON('/url', startDate, endDate)
      .then(done);
    $httpBackend.flush();
  });

  it('Should format date correctly from timestamp', function (done) {
    $httpBackend.expectPOST('/url', {
      start: '2015-09-14T10',
      finish: '2015-09-14T11',
      report_format: 'json',
      report_type: 'simple'
    }).respond({status: 'completed'});

    var startDate = new Date(1442228390000);
    var endDate = new Date(1442229000000);

    reportService.getJSON('/url', startDate, endDate)
      .then(done);
    $httpBackend.flush();
  });

  it('Should download report', function (done) {
    $httpBackend.whenPOST('/url').respond('some;csv');
    spyOn(fileSaver, 'saveFileFromHttp');

    reportService.downloadReport('/url', startDate, endDate, 'csv')
      .then(done);

    $httpBackend.flush();
    expect(fileSaver.saveFileFromHttp).toHaveBeenCalled();
  });

  it('Should download receipts', function (done) {
    $httpBackend.whenPOST('/api/report/receipts').respond('some;csv');
    spyOn(fileSaver, 'saveFileFromHttp');

    reportService.downloadReceipts(startDate, endDate, 'ru_ru')
      .then(done);

    $httpBackend.flush();
    expect(fileSaver.saveFileFromHttp).toHaveBeenCalled();
  });

  it('Should download usage report', function (done) {
    $httpBackend.whenPOST('/api/report/usage').respond('some;csv');
    spyOn(fileSaver, 'saveFileFromHttp');

    reportService.downloadUsage(startDate, endDate, 'ru_ru')
      .then(done);

    $httpBackend.flush();
    expect(fileSaver.saveFileFromHttp).toHaveBeenCalled();
  });
});
