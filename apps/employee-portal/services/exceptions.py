class DepartmentAccessConflict(Exception):
    def __init__(self, roles):
        self.roles = list(roles)

        super().__init__(
            "User has access roles for multiple departments."
        )