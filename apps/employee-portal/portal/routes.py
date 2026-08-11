from flask import Blueprint,render_template


bp_portal = Blueprint("portal", __name__)
@bp_portal.route("/")
def home():
    return render_template("home.html")