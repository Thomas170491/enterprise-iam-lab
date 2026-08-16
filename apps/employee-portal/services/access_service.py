from extensions import db
from models import Department


def get_department(user):
    stmt = db.select(Department).where(
        Department.client_role.in_(user.client_roles)
    )

    return db.session.execute(stmt).scalars().first()


def get_department_resources(user):
    department = get_department(user)

    if department is None:
        return None

    return {
        "department": department.name,
        "resources": [
            resource.name
            for resource in department.resources
        ],
    }


def get_access(user):
    return {
        "realm_roles": list(user.realm_roles),
        "client_roles": list(user.client_roles),
    }