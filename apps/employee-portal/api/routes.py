from flask import Blueprint, jsonify, g


from api.decorators import api_login_required
from api.errors import api_error

from services.identity_service import get_identity
from services.access_service import (
    get_access,
    get_department_resources,
)
from services.exceptions import DepartmentAccessConflict


bp_api = Blueprint(
    "api",
    __name__,
    url_prefix="/api/v1",
)


@bp_api.get("/me")
@api_login_required
def me():
    return jsonify(
        get_identity(g.api_user)
    )


@bp_api.get("/access")
@api_login_required
def access():
    return jsonify(
        get_access(g.api_user)
    )


@bp_api.get("/department")
@api_login_required
def department():
    try:
        department_data = get_department_resources(g.api_user)

    except DepartmentAccessConflict:
        return api_error(
            "access_conflict",
            "Conflicting department access detected.",
            409,
        )

    if department_data is None:
        return api_error(
            "department_access_not_found",
            "No department access is assigned.",
            403,
        )

    return jsonify(department_data)