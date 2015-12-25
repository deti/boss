# -*- coding: utf-8 -*-

import conf
import errors
import logbook
import bottle
import posixpath
from urllib.parse import urljoin
from memdb.token import UserToken
from model import User, autocommit, MessageTemplate
from model import display
from memdb.token import PasswordResetToken
from api import get, post, put, delete, AdminApi, local_properties, request_base_url, options, ADMIN_TOKEN_NAME, \
    enable_cors
from api.check_params import check_params
from api.validator import Date, IndexSizeLimit, FilterMode, IntRange, Email, Visibility, String, \
    TokenId, List, StringWithLimits, ValidateError, Bool, ModelId, SortFields
from api.admin.role import TokenAdmin, TokenManager, Roles
from model.account.role import Role
from utils.i18n import preferred_language


UserIdExpand = ModelId(User, errors.UserNotFound)


class PasswordResetTokenValidator(object):
    def __call__(self, value):
        try:
            return PasswordResetToken.get(value)
        except errors.PasswordResetTokenInvalid as e:
            raise ValidateError(e.message)


PasswordValidator = StringWithLimits(conf.user.min_password_length, conf.user.max_password_length)


class UserApi(AdminApi):
    ADMIN_FRONTEND_PATH = "/admin/"

    @post("user/")
    @check_params(
        token=TokenManager,
        email=(Email, IndexSizeLimit),
        password=PasswordValidator,
        role=Roles,
        name=StringWithLimits(max_length=256),
    )
    @autocommit
    def new_user(self, token, email, role, password=None, name=None):
        """
        Registration of new user.

        :param Email email: User email (Email_);
        :param str password: User Password. If the it is empty then the password
                             recovery email will be sent to the email.
        :param str role: User role.
        :param str name: User display name [optional]

        :returns dict user_info: User info.

        **Example**::

            {
                "user_info": {
                    {"name": "Super Admin",
                     "deleted": null,
                     "email": "admin@test.ru",
                     "role": {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                              'role_id': 'admin'}
                     "created": "2015-04-24T11:14:22"}
                }
            }

        """
        if not Role.validate(token.role, role):
            raise errors.UserInvalidRole()

        if token.role != Role.ADMIN and token.role == role:
            # user can administrate only users with low priority
            raise errors.UserInvalidRole()

        user_info = User.new_user(email, password, role, name=name)

        if not password:
            self.send_password_reset_email(email, request_base_url(), for_new_user=True)

        return {"user_info": display(user_info)}

    @post('auth/')
    @enable_cors
    @check_params(email=(Email, IndexSizeLimit), password=PasswordValidator, return_user_info=Bool)
    def login(self, email, password, return_user_info=False):
        """
        Auth user by email and password. This method setup cookie which can be used in next requests.

        :param Email email: User Email_.
        :param str password: User password (flat text).
        :param Bool return_user_info: Return user info of logged user.

        :return dict user_info: User info

        **Example**::

            {
                "user_info": {
                    {"name": "Super Admin",
                     "deleted": null,
                     "email": "admin@test.ru",
                     "role": {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                              'role_id': 'admin'}
                     "created": "2015-04-24T11:14:22"}
                }
            }

        """
        new_token, user_info = User.login(email, password)
        setattr(local_properties, 'user_token', new_token)
        cookie_flags = {"httponly": True}
        if conf.api.secure_cookie and not conf.test:
            cookie_flags["secure"] = True
        bottle.response.set_cookie(ADMIN_TOKEN_NAME, new_token.id, path="/", **cookie_flags)
        user_info = display(user_info) if return_user_info else {}
        return {"user_info": user_info}

    @options('auth/')
    @enable_cors
    def login_options(self):
        r = bottle.HTTPResponse("")
        r.content_type = "text/html"
        return r

    @post('logout/')
    @check_params(token=TokenId)
    def logout(self, token):
        """
        Stop user session.
        """
        UserToken.remove(token)
        bottle.response.delete_cookie("token", path="/")
        return {}

    @get('user/me/')
    @check_params(token=TokenId)
    def get_info(self, token):
        """
        Return user info of current user.

        :return dict user_info: User info

        **Example**::

            {
                "user_info": {
                    {"name": "Super Admin",
                     "deleted": null,
                     "email": "admin@test.ru",
                     "role": {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                              'role_id': 'admin'}
                     "created": "2015-04-24T11:14:22"}
                }
            }
        """
        user = User.get_by_id(token.user_id)
        if user is None:
            logbook.debug("User not found by id {}", token.user_id)
            raise errors.UserInvalidToken()
        return {"user_info": display(user)}

    @get('user/<user_id>/')
    @check_params(
        token=TokenId,
        user_id=ModelId)
    def get_others_info(self, user_id):
        """
        returns user info

        :param user user_id: user id

        :return dict user_info: the dict has the same structure as result of
                                method :obj:`get /0/user/me/ <view.get /0/user/me>`
        """
        user = User.get_by_id(user_id)
        if user is None:
            raise errors.UserNotFound()
        return {"user_info": display(user)}

    # noinspection PyUnusedLocal
    @put('user/me/')
    @check_params(
        all_parameters=True,
        token=TokenId,
        password=PasswordValidator,
        name=StringWithLimits(max_length=256),
        email=(Email, IndexSizeLimit)
    )
    @autocommit
    def update(self, token, all_parameters, password=None, name=None, email=None):
        """
        Update user self profile.

        :param str password: New password [optional]
        :param str name: New name [optional]
        :param str email: New email [optional]

        :return dict user_info: User info
        """
        return self.update_user_common(User.get_by_id(token.user_id), all_parameters)

    # noinspection PyUnusedLocal
    @put('user/<user>/')
    @check_params(
        all_parameters=True,
        token=TokenAdmin,
        user=UserIdExpand,
        password=PasswordValidator,
        name=StringWithLimits(max_length=256),
        email=(Email, IndexSizeLimit),
        role=Roles
    )
    @autocommit
    def update_other(self, token, user, all_parameters, password=None,
                     name=None, email=None, role=None):
        """
        Update user profile of other user.

        :param User user: User id
        :param str password: New password [optional]
        :param str name: New name [optional]
        :param str email: New email [optional]

        :return dict user_info: Dict with user info, as in :obj:`PUT /0/user/me/ <view.PUT /0/user/me>`
        """
        all_parameters.pop("user", None)
        return self.update_user_common(user, all_parameters)

    @staticmethod
    def update_user_common(user, all_parameters):
        if not all_parameters:
            raise errors.NothingForUpdate()
        user.update(all_parameters)
        return {"user_info": display(user)}

    @delete('user/me/')
    @check_params(token=TokenId)
    @autocommit
    def remove(self, token):
        """
        Mark myself user as removed

        :return: None
        """
        user = User.get_by_id(token.user_id)
        if not user.mark_removed():
            raise errors.UserRemoved()
        return {}

    @delete('user/<user>/')
    @check_params(
        token=TokenAdmin,
        user=UserIdExpand
    )
    @autocommit
    def remove_other(self, token, user):
        """
        Mark user as removed

        :param: None
        """
        logbook.info("Deleting user {} by {}", user, token.user_id)
        if int(token.user_id) == user.user_id:
            raise errors.HarakiriIsNotAllowed()
        if not user.mark_removed():
            raise errors.UserRemoved()
        return {}

    @delete('user/password_reset/')
    @check_params(email=(Email, IndexSizeLimit))
    def request_password_reset(self, email):
        """
        Sent email with link to reset password

        :param Email email: Email_ - user email

        :return: None.
        """
        self.send_password_reset_email(email, request_base_url())
        return {}

    @post('user/password_reset/<password_token>/')
    @check_params(password_token=PasswordResetTokenValidator, password=PasswordValidator)
    @autocommit
    def password_reset(self, password_token, password):
        """
        Reset user password

        :param PasswordResetToken password_token:  Token which was returned by method
                :obj:`POST /0/user/request_password_reset/ <view.POST /0/user/request_password_reset>`;
        :param str password: New password.

        :return: None
        """
        # noinspection PyUnresolvedReferences
        user = User.get_by_id(password_token.user_id)
        user.password_reset(password)
        UserToken.remove_by(user.user_id)
        PasswordResetToken.remove(password_token)
        return {}

    # noinspection PyUnusedLocal
    @get('user/password_reset/<password_token>/')
    @check_params(password_token=PasswordResetTokenValidator)
    def validate_password_reset(self, password_token):
        """
        Checks that password reset token is valid.

        :param PasswordResetToken password_token: Token which was returned by method
                :obj:`POST /0/user/request_password_reset/ <view.POST /0/user/request_password_reset>`.

        :return: None.
        """
        return {}

    # noinspection PyUnusedLocal
    @get('user/')
    @check_params(
        token=TokenId,
        role=Roles,
        role_list=List(Roles),
        name=String,
        visibility=Visibility,
        deleted_before=Date(), deleted_after=Date(),
        email=String,
        created_before=Date(), created_after=Date(),
        page=IntRange(1),
        limit=IntRange(1, conf.api.pagination.limit),
        sort=List(SortFields(User)),  # Sort(User.Meta.sort_fields),
        all_parameters=True
    )
    def list(self, email=None, role=None,
             role_list=None, name=None,
             visibility=Visibility.DEFAULT,
             deleted_before=None, deleted_after=None,
             created_before=None, created_after=None,
             page=1, limit=conf.api.pagination.limit,
             sort=('email',), all_parameters=True):
        """
        Return filtered user list.

        :param str email: Mask for email
        :param Role role: Role_ - user role
        :param List role_list: user role list
        :param str visibility: Visibility options
                               *visible* - Only active users, [by default]
                               *deleted* - Only removed users.
                               *all* - All users.
        :param Date deleted_before: Date_ - Filter users which were archived before this date.
        :param Date deleted_after: Date_ - Filter users which were archived after this date.
        :param Date created_before: Date_ - Filter users which were created before this date.
        :param Date created_after: Date_ - Filter users which were created after this date.
        :param int page: Page
        :param int limit: Number of elements per page
        :param str visibility: Visibility options
                               *visible* - Only active customers, [by default]
                               *deleted* - Only removed customers.
                               *all* - All customers.
        :param str or List sort: Field name or list of field names which is used for sorting.
                                 Ascending sort is default.
                                 For descending sort use "-" before name.
                                 Default sorting field: ('email');

        :return List user_list: List of users for this query.

        **Example**::

            {
                "user_list": {
                    "total": 2,
                    "limit": 200,
                    "offset": 0
                    "items": [
                    {
                        "name": null,
                        "created": "2013-09-19T06:42:03.747000+00:00",
                        "deleted": null,
                        "role": {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                                 'role_id': 'admin'}
                        "user_id": "523a9cbb312f9120c41b96b5",
                        "email": "list_test0@test.ru"
                    },
                    {
                        "name": null,
                        "created": "2013-09-19T06:42:03.823000+00:00",
                        "deleted": null,
                        "role": {'localized_name': {'en': 'Administrator', 'ru': 'Администратор'},
                                 'role_id': 'admin'}
                        "user_id": "523a9cbb312f9120c41b96b6",
                        "email": "list_test1@test.ru"
                    }]}
            }
        """
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("limit", limit)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("page", page)
        # noinspection PyUnresolvedReferences
        all_parameters.setdefault("sort", sort)
        query = None

        if role_list:
            query = User.query.filter(User.role.in_(role_list))

        query = User.api_filter(all_parameters, query=query, visibility=visibility)
        return {"user_list": self.paginated_list(query)}

    @staticmethod
    def send_password_reset_email(email, base_url, for_new_user=False):
        from task.mail import send_email
        user = User.get_by_email(email, include_deleted=False)
        if user is None:
            raise errors.UserNotFound()
        token = PasswordResetToken.create(user)
        url = urljoin(base_url, posixpath.join(UserApi.ADMIN_FRONTEND_PATH,
                                               "set-password/{}".format(token.id)))
        template_id = MessageTemplate.NEW_USER if for_new_user else MessageTemplate.USER_PASSWORD_RESET
        url_name = "activate_url" if for_new_user else "password_reset_url"
        params = {url_name: url}

        subject, body = MessageTemplate.get_rendered_message(template_id, language=preferred_language(),
                                                             user_name=user.name, **params)

        send_email.delay(email, subject, body)
        return user
