const dependencies = ['restangular'];

export default angular.module('boss.userService', dependencies)
  .factory('userService', function (Restangular) {
    var Users = Restangular.all('user');
    var transformFromServer = function (user) {
      user.roleInfo = user.role;
      user.role = user.role.role_id;
      return user;
    };
    Restangular.addResponseInterceptor(function (data, operation, what) {
      if (what === 'user') {
        if (operation === 'getList') {
          var extractedData = data.user_list.items;
          extractedData = extractedData.map(transformFromServer);
          extractedData.total = data.user_list.total;
          extractedData.perPage = data.user_list.per_page;
          return extractedData;
        }
        if (operation === 'post' || operation === 'put') {
          data = transformFromServer(data.user_info);
        }
      }
      return data;
    });

    return {
      create: function (user) {
        return Users.post({
          email: user.email,
          role: user.role,
          name: user.name
        });
      },
      getList: function (args) {
        return Users.getList(args);
      },
      archiveMe: function () {
        return Restangular.one('user').one('me').remove();
      },
      archiveUser: function (user) {
        return user.remove();
      }
    };
  });
