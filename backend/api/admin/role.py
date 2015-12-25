import errors
from api.validator import TokenId, Choose
from model.account.role import Role


class TokenRole(TokenId):
    def __init__(self, role):
        self.role = role
        super().__init__()

    def __call__(self, value):
        token = super().__call__(value)
        if not Role.validate(token.role, self.role):
            raise errors.UserInvalidRole()
        return token


class TokenAdmin(TokenRole):
    def __init__(self):
        super().__init__(Role.ADMIN)


class TokenAccount(TokenRole):
    def __init__(self):
        super().__init__(Role.ACCOUNT)


class TokenManager(TokenRole):
    def __init__(self):
        super().__init__(Role.MANAGER)


class TokenSupport(TokenRole):
    def __init__(self):
        super().__init__(Role.SUPPORT)


Roles = Choose(Role.ROLE_LIST)
