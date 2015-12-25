const dependencies = ['restangular'];

export default angular.module('boss.currentUserService', dependencies)
  .factory('currentUserService', function (Restangular, $q) {
    var currentUser = null;
    return {
      userInfo: function () {
        if (currentUser) {
          return $q.when(currentUser);
        }
        return Restangular.all('user').get('me').then(function (rsp) {
          currentUser = rsp.user_info;
          return currentUser;
        });
      },
      auth: function (login, password) {
        return Restangular.one('auth').post('', {
          email: login,
          password: password,
          return_user_info: 'true'
        }).then(function (rsp) {
          currentUser = rsp.user_info;
        });
      },
      resetPassword: function (email) {
        return Restangular.one('user').customDELETE('password_reset', {
          email: email
        });
      },
      resetPasswordIsValid: function (token) {
        return Restangular.one('user').one('password_reset').one(token).get()
          .then(function () {
            return true;
          })
          .catch(function () {
            return false;
          });
      },
      setPassword: function (password, token) {
        return Restangular.one('user').one('password_reset').one(token).post('', {
          password_token: token,
          password: password
        });
      },
      logout: function () {
        return Restangular.one('logout').post().then(function () {
          currentUser = null;
        });
      }
    };
  });
