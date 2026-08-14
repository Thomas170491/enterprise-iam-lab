from flask import Blueprint,render_template,session,abort
from flask_login import login_required, current_user
from auth.decorators import client_role_required


bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
    user = session.get("user")

    return render_template(
        "home.html",
        user = user
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

    # TODO: derive department from authoritative identity attribute later
    department_roles = {
    "hr-data-viewer": "Human Resources",
    "finance-data-viewer": "Finance",
    "it-data-viewer": "Information Technology",
    "operations-data-viewer": "Operations",
    "security-data-viewer": "Security",
}
    department_name = None

    for role in current_user.client_roles:
        if role in department_roles:
            department_name = department_roles[role]
            break
    if department_name is None:
      abort(403)

    return render_template(
    "department.html",
    department=department_name
)


