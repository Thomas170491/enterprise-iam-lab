from flask import Blueprint, render_template,current_app,request
from flask_login import login_required
from auth.decorators import client_role_required
from auth.permissions import IAM_DASHBOARD_ACCESS,IDENTITY_VIEWER, AUDIT_LOG_VIEWER
from services.identity_service import search_identities, get_identity_access
from services.exceptions import KeycloakAdminAPIError, AuditPersistenceError
from services.audit_service import record_audit_event, get_recent_audit_events





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

@bp_governance.get("/identities/<user_id>")
@login_required
@client_role_required(IDENTITY_VIEWER)
def identity_detail(user_id):
    try:
        identity_access= get_identity_access(
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            user_id=user_id,
            target_client_name=current_app.config["KEYCLOAK_CLIENT_ID"]
        )
    except KeycloakAdminAPIError: 
        current_app.logger.exception("Failed to retrieve identity access")

        return render_template(
            "identity-detail-error.html"
        ), 502

    try :  
        record_audit_event(
            actor_user_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            actor_username=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            action="identity.view",
            target_type="identity",
            target_id=user_id,
            target_name=identity_access["identity"].get("username"),
            outcome="success",
            details={
                "source": "governance-portal"
            },
        )
    except AuditPersistenceError:
        current_app.logger.exception("Failed to persist audit event for identity view")

    return render_template(
        "identity_detail.html",
        identity_access=identity_access
    )
@bp_governance.get("/audit")
@login_required
@client_role_required(AUDIT_LOG_VIEWER)
def audit_log():
        events = get_recent_audit_events(
            limit=100
        )

        return render_template(
            "audit-log.html",
            events=events,
        )



