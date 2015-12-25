import './popupErrorService';

describe('popupErrorService', function () {
  var popupErrorService,
    toaster;
  beforeEach(angular.mock.module('boss.popupErrorService'));

  beforeEach(inject(function (_popupErrorService_, _toaster_) {
    popupErrorService = _popupErrorService_;
    toaster = _toaster_;
    spyOn(toaster, 'pop');
  }));

  it('Should pass dummy test', function () {
    expect(popupErrorService).toBeTruthy();
  });

  it('Should pop error from simple object', function () {
    var message = {
      localized_message: 'trouble'
    };

    popupErrorService.show(message);
    expect(toaster.pop).toHaveBeenCalledWith('error', 'trouble');
  });

  it('Should pop error from restangular response object', function () {
    var message = {
      data: {
        localized_message: 'trouble'
      }
    };

    popupErrorService.show(message);
    expect(toaster.pop).toHaveBeenCalledWith('error', 'trouble');
  });

  it('Should pop "server error" message when called with object without any info', function () {
    popupErrorService.show({});
    expect(toaster.pop).toHaveBeenCalledWith('error', 'Server error');
  });
});
