const dependencies = [];

export default angular.module('boss.addressService', dependencies)
  .factory('addressService', function () {
    var isSameAddress = function (user) {
      var rtn = (user.detailed_info.legal_address_country &&
      user.detailed_info.legal_address_city &&
      user.detailed_info.legal_address_address &&
      user.detailed_info.legal_address_country === user.detailed_info.location_country &&
      user.detailed_info.legal_address_city === user.detailed_info.location_city &&
      user.detailed_info.legal_address_address === user.detailed_info.location_address);

      return !!rtn;
    };

    var setAddress = function (user, same) {
      user.detailed_info.location_country = same ? user.detailed_info.legal_address_country : null;
      user.detailed_info.location_city = same ? user.detailed_info.legal_address_city : null;
      user.detailed_info.location_address = same ? user.detailed_info.legal_address_address : null;
    };

    return {
      isTheSame: isSameAddress,
      set: setAddress
    };
  });
