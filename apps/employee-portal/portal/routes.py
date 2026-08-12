from flask import Blueprint,render_template,session


bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
    user = session.get("user")

    return render_template(
        "home.html",
        user = user
        )