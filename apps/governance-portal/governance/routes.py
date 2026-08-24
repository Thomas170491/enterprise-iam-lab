from flask import Blueprint, render_template
from flask_login import login_required
from auth.decorators import client_role_required
from auth.permissions import IAM_DASHBOARD_ACCESS


bp_governance = Blueprint(
    "governance",
    __name__,
)


@bp_governance.get("/")
@login_required
@client_role_required(IAM_DASHBOARD_ACCESS)
def dashboard():
    """
    Render the Governance Portal dashboard.

    """
    return render_template(
        "dashboard.html"
    )