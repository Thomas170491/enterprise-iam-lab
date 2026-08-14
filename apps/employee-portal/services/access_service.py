from portal.department_data import DEPARTMENT_RESOURCES, DEPARTMENT_ROLES


def get_department(user):
    for role in user.client_roles:
        if role in DEPARTMENT_ROLES:
            return DEPARTMENT_ROLES[role]

    return None


def get_department_resources(user):
    department = get_department(user)

    if department is None:
        return None

    return {
        "department": department,
        "resources": DEPARTMENT_RESOURCES.get(department, []),
    }


def get_access(user):
    return {
        "realm_roles": list(user.realm_roles),
        "client_roles": list(user.client_roles),
    }