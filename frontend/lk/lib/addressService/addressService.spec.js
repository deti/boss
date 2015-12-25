describe('addressService', function () {
  var addressService;

  beforeEach(module('boss.addressService'));

  beforeEach(inject(function (_addressService_) {
    addressService = _addressService_;
  }));

  it('should check if addresses is the same', function () {
    var user = {
      detailed_info: {
        legal_address_city: 'foo city',
        legal_address_address: 'foo address',
        legal_address_country: 'foo country',
        location_country: 'foo country',
        location_city: 'foo city',
        location_address: 'foo address'
      }
    };
    expect(addressService.isTheSame(user)).toBe(true);

    user = {
      detailed_info: {
        legal_address_city: 'foo city',
        legal_address_address: 'foo address',
        legal_address_country: 'foo country',
        location_country: 'bar country',
        location_city: ' city',
        location_address: 'foo address'
      }
    };
    expect(addressService.isTheSame(user)).toBe(false);
  });

  it('should set location address', function () {
    var user = {
      detailed_info: {
        legal_address_city: 'foo city',
        legal_address_address: 'foo address',
        legal_address_country: 'foo country'
      }
    };
    addressService.set(user, true);
    expect(user.detailed_info.location_country).toBe('foo country');
    expect(user.detailed_info.location_address).toBe('foo address');
    expect(user.detailed_info.location_city).toBe('foo city');

    addressService.set(user, false);
    expect(user.detailed_info.location_country).toBe(null);
    expect(user.detailed_info.location_address).toBe(null);
    expect(user.detailed_info.location_city).toBe(null);
  });

});
