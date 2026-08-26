from flask import Blueprint, render_template,current_app,request
from flask_login import login_required
from auth.decorators import client_role_required
from auth.permissions import IAM_DASHBOARD_ACCESS,IDENTITY_VIEWER
from services.identity_service import search_identities 

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

@bp_governance.get("/identities")
@login_required
@client_role_required(IDENTITY_VIEWER)
def identities():
    search = request.args.get(
        "search",
        default="",
        type=str,
    ).strip()

    has_searched = "search" in request.args

    identities = [] 

    if has_searched :
        identities = search_identities(
            admin_api_url=current_app.config[
                "KEYCLOAK_ADMIN_API_URL"
            ],
            token_url=current_app.config[
                "KEYCLOAK_TOKEN_URL"
            ],
            client_id=current_app.config[
                "KEYCLOAK_SERVICE_CLIENT_ID"
            ],
            client_secret=current_app.config[
                "KEYCLOAK_SERVICE_CLIENT_SECRET"
            ],
            search=search,
        )

    return render_template(
        "identities.html",
        search=search,
        identities=identities,
    )