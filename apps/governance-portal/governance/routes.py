from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
    abort,
)

from flask_login import login_required,current_user
from auth.decorators import client_role_required
from auth.permissions import IAM_DASHBOARD_ACCESS,IDENTITY_VIEWER, AUDIT_LOG_VIEWER,ROLE_MANAGER
from services.identity_service import search_identities, get_identity_access
from services.exceptions import KeycloakAdminAPIError, AuditPersistenceError, AuditQueryError,RoleAdministrationPolicyError
from services.audit_service import record_audit_event, get_recent_audit_events
from services.role_service import assign_identity_client_role, remove_identity_client_role




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
            target_client_name="employee-portal"
        )

        direct_role_names = {
        role["name"] for role in identity_access["direct_client_roles"]
        }

    except KeycloakAdminAPIError: 
        current_app.logger.exception("Failed to retrieve identity access")

        return render_template(
            "identity-detail-error.html"
        ), 502

    try :  
        record_audit_event(
            actor_user_id=current_user.sub,
            actor_username=current_user.username,
            action="identity.view",
            target_type="identity",
            target_id=user_id,
            target_name=identity_access["identity"].get("username"),
            outcome="success",
            details={
                "source": "governance-portal",
                "service_client": current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"]
            },
        )
    except AuditPersistenceError:
        current_app.logger.exception("Failed to persist audit event for identity view")

    return render_template(
        "identity_detail.html",
        identity_access=identity_access,
        direct_role_names=direct_role_names

    )
@bp_governance.get("/audit")
@login_required
@client_role_required(AUDIT_LOG_VIEWER)
def audit_log():
    try:
        events = get_recent_audit_events(
            limit=100
        )

    except AuditQueryError:
        current_app.logger.exception(
            "Failed to retrieve audit log"
        )

        return render_template(
            "audit-log-error.html"
        ), 503

    return render_template(
        "audit-log.html",
        events=events,
    )

@bp_governance.post("/identities/<user_id>/roles")
@login_required
@client_role_required(ROLE_MANAGER)
def assign_identity_role(user_id):
    """
    Assign an Employee Portal client role to an identity.

    Only authenticated users possessing the Governance
    ROLE_MANAGER permission may perform this operation.
    """
    role_name = request.form.get("role_name", "").strip()

    if not role_name :
        abort(400)

    try :
        assign_identity_client_role (
       
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
            user_id=user_id,

                       # Do NOT trust the browser to choose the client.
            #
            # The Governance Portal currently administers
            # Employee Portal application access only.
            target_client_name="employee-portal",

            role_name=role_name,

            # The logged-in human remains the audit actor.
            actor_user_id=current_user.sub,
            actor_username=current_user.username,

        )
    
    except RoleAdministrationPolicyError:
        current_app.logger.warning("Role assignment rejected by the Governance Policy")
        abort(403)

    except AuditPersistenceError:
        #role service is fail-closed
        #the Keycloak mutation has not happend when
        #the initail audit write fails
        current_app.logger.exception("Role assignment blocked because audit persistance failed")
        abort(503)

    except KeycloakAdminAPIError:
        current_app.logger.exception("Keycloak role assignment failed")
        abort(502)

    return redirect(
        url_for(
            "governance.identity_detail", 
            user_id = user_id
            )
    )

@bp_governance.post("/identities/<user_id>/roles/<role_name>/remove")
@login_required
@client_role_required(ROLE_MANAGER)
def remove_identity_role(user_id,role_name):
    """
    Assign an Employee Portal client role to an identity.

    Only authenticated users possessing the Governance
    ROLE_MANAGER permission may perform this operation.
    """
    role_name =  role_name.strip()

    if not role_name :
        abort(400)

    try :
        remove_identity_client_role (
         
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
            user_id=user_id,

                       # Do NOT trust the browser to choose the client.
            #
            # The Governance Portal currently administers
            # Employee Portal application access only.
            target_client_name="employee-portal",

            role_name=role_name,

            # The logged-in human remains the audit actor.
            actor_user_id=current_user.sub,
            actor_username=current_user.username,

        )
    
    except RoleAdministrationPolicyError:
        current_app.logger.warning("Role removal rejected by the Governance Policy")
        abort(403)

    except AuditPersistenceError:
        #role service is fail-closed
        #the Keycloak mutation has not happend when
        #the initail audit write fails
        current_app.logger.exception("Role removal blocked because audit persistance failed")
        abort(503)

    except KeycloakAdminAPIError:
        current_app.logger.exception("Keycloak role removal failed")
        abort(502)

    return redirect(
        url_for(
            "governance.identity_detail", 
            user_id = user_id
            )
    )