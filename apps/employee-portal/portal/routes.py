from flask import Blueprint,render_template,abort
from flask_login import login_required, current_user
from auth.decorators import client_role_required
from services.access_service import get_department_resources
from services.identity_service import get_identity
from services.exceptions import DepartmentAccessConflict

bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
  
    return render_template(
        "home.html",
        )

@bp_portal.route("/profile")
@login_required
def profile():
    user = get_identity(current_user)
    return render_template(
        "profile.html",
         user = user                  
 )

@bp_portal.route("/manager")
@login_required
@client_role_required("manager-dashboard")
def manager():
    return render_template("manager.html")

@bp_portal.route("/department")
@login_required
def department():
    try:
        department_data = get_department_resources(current_user)
    except DepartmentAccessConflict:
        abort(
            409,
            description = "Conflicting department access detected",
        )

    if not department_data:
        abort(403)


    return render_template(
    "department.html",
    department=department_data["department"],
    resources=department_data["resources"]
)

