from flask import Blueprint, render_template


bp_governance = Blueprint(
    "governance",
    __name__,
)


@bp_governance.get("/")
def dashboard():
    """
    Render the Governance Portal dashboard.

    """
    return render_template(
        "dashboard.html"
    )