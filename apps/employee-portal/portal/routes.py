from flask import Blueprint,render_template,session
from flask_login import login_required, current_user


bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
    user = session.get("user")

    return render_template(
        "home.html",
        user = user
        )
@login_required
@bp_portal.route("/profile")
def profile():
    return render_template(
        "profile.html",
         user = current_user                  
 )