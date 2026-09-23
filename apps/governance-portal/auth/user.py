from flask_login import UserMixin


class User(UserMixin):
    def __init__(
        self,
        sub: str,
        username: str | None,
        name: str | None,
        email: str | None,
        client_roles: list[str],
        realm_roles: list[str],
    ) -> None:
        self.id = sub
        self.sub = sub
        self.username = username
        self.name = name
        self.email = email
        self.client_roles = client_roles
        self.realm_roles = realm_roles
