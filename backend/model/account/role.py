import conf


class Role:
    ADMIN = "admin"
    ACCOUNT = "account"
    MANAGER = "manager"
    SUPPORT = "support"

    ROLES = {
        ADMIN: 4,
        ACCOUNT: 3,
        MANAGER: 2,
        SUPPORT: 1
    }

    ROLE_LIST = frozenset(ROLES.keys())

    @classmethod
    def validate(cls, validated_role, minimal_accessible_role):
        p1 = cls.priority(validated_role)
        p2 = cls.priority(minimal_accessible_role)
        return p1 >= p2

    @classmethod
    def priority(cls, role):
        return cls.ROLES.get(role, 0)

    @classmethod
    def lower_roles(cls, role):
        """
        Return roles which are lower prioritized than passed
        """
        priority = cls.priority(role)
        return frozenset(r for r, p in cls.ROLES.items() if p < priority)

    @classmethod
    def higher_roles(cls, role):
        """
        Return roles which are higher prioritized than passed
        """
        priority = cls.priority(role)
        return frozenset(r for r, p in cls.ROLES.items() if p > priority)

    @classmethod
    def display(cls, role, short=False):
        if short:
            return role
        return {"localized_name": conf.role[role], "role_id": role}
