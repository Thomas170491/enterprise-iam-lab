from flask import Blueprint,render_template,abort
from flask_login import login_required, current_user
from auth.decorators import client_role_required
from portal.department_data import DEPARTMENT_ROLES, DEPARTMENT_RESOURCES


bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
  
    return render_template(
        "home.html",
        )

@bp_portal.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
         user = current_user                  
 )

@bp_portal.route("/manager")
@login_required
@client_role_required("manager-dashboard")
def manager():
    return render_template("manager.html")

@bp_portal.route("/department")
@login_required
def department():


    department_name = None

    for role in current_user.client_roles:
        if role in DEPARTMENT_ROLES:
            department_name = DEPARTMENT_ROLES[role]
            break
    if department_name is None:
      abort(403)

    resources = DEPARTMENT_RESOURCES.get(
    department_name,
    [])

    return render_template(
    "department.html",
    department=department_name,
    resources=resources
)


