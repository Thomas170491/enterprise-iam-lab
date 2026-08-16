from flask import Blueprint, jsonify
from flask_login import current_user

from api.decorators import api_login_required
from services.identity_service import get_identity 
from services.access_service import get_access, get_department_resources

bp_api = Blueprint("api", __name__, url_prefix="/api/v1")

@bp_api.get("/me") 
@api_login_required
def me():
    return jsonify(
         get_identity(current_user)
)

@bp_api.get("/access")
@api_login_required
def access():
    return jsonify(
     get_access(current_user)   
    )

@bp_api.get("/department")
@api_login_required
def department(): 
    try :
        department_data = get_department_resources(current_user)
    except ValueError:
        return jsonify({
            "errror" : "access_conflicted",
            "message" : "Conflicting department access detected"
        }), 409

    if not department_data:
        return jsonify(
            {
                "error" : "department_access_not_found",
                "message" : "No department access is defined"
            }
        )

    return jsonify(department_data)