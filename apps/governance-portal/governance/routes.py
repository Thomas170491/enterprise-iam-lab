from flask import (
    Blueprint,
    json,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
    abort,
)
from datetime import datetime, timezone
from flask_login import login_required,current_user
from auth.decorators import client_role_required
from auth.permissions import (
    IAM_DASHBOARD_ACCESS,IDENTITY_VIEWER, 
    AUDIT_LOG_REVIEWER,ROLE_MANAGER,
    ACCESS_REVIEWER,
    ACCESS_REVIEW_MANAGER,       
)
from services.identity_service import search_identities, get_identity_access
from services.exceptions import KeycloakAdminAPIError, AuditPersistenceError, AuditQueryError,RoleAdministrationPolicyError
from services.audit_service import record_audit_event, get_recent_audit_events
from services.role_service import assign_identity_client_role, remove_identity_client_role,get_managed_roles
from services.access_review_service import( 
    get_access_reviews_for_reviewer,
    get_access_review_for_reviewer,
    create_access_review_with_audit,
    get_access_review_for_manager,
    get_access_reviews_for_manager
)
from sqlalchemy.exc import SQLAlchemyError





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

        managed_roles = get_managed_roles("employee-portal")

    except KeycloakAdminAPIError: 
        current_app.logger.exception("Failed_to_retrieve_identity_access")

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
        direct_role_names=direct_role_names,
        managed_roles=managed_roles

    )
@bp_governance.get("/audit")
@login_required
@client_role_required(AUDIT_LOG_REVIEWER)
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
            # The Governance Portal currently administers
            # Employee Portal application access only.
            target_client_name="employee-portal",

            role_name=role_name,

            # The logged-in human remains the audit actor.
            actor_user_id=current_user.sub,
            actor_username=current_user.username,

        )
    
    except RoleAdministrationPolicyError as exc:
        current_app.logger.warning(
            "Role assignment rejected by Governance policy: %s",
            exc.reason,
        )

        sod_messages = {
            "sod_deny": (
                "This role combination violates a segregation-of-duties rule. "
                "No role was assigned."
            ),
            "sod_requires_review": (
                "This role assignment requires review. "
                "No role was assigned."
            ),
        }

        if exc.reason in sod_messages:
            return render_template(
                "role-assignment-blocked.html",
                message=sod_messages[exc.reason],
            ), 403

        abort(403)
    except AuditPersistenceError:
        #role service is fail-closed
        #the Keycloak mutation has not happend when
        #the initail audit write fails
        current_app.logger.exception("Role_assignment_blocked_because_audit_persistance_failed")
        abort(503)

    except KeycloakAdminAPIError:
        current_app.logger.exception("Keycloak_role_assignment_failed")
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
        current_app.logger.warning("Role_removal_rejected_by_the_Governance_Policy")
        abort(403)

    except AuditPersistenceError:
        #role service is fail-closed
        #the Keycloak mutation has not happend when
        #the initail audit write fails
        current_app.logger.exception("Role_removal_blocked_because_audit_persistance_failed")
        abort(503)

    except KeycloakAdminAPIError:
        current_app.logger.exception("Keycloak_role_removal_failed")
        abort(502)

    return redirect(
        url_for(
            "governance.identity_detail", 
            user_id = user_id
            )
    )

@bp_governance.get("/access-reviews")
@login_required
@client_role_required(ACCESS_REVIEWER)

def access_reviews():
    """
    Display access review campaigns assigned to the authenticated reviewer.
    """
    
    reviews = get_access_reviews_for_reviewer(current_user.get_id())
    
    return render_template(
        "access-reviews.html",
        reviews=reviews,
    )

@bp_governance.get("/access-reviews/<int:review_id>")
@login_required
@client_role_required(ACCESS_REVIEWER)
def access_review_detail(review_id):
    """
    Display a campaign and its snapshots to the assigned reviewer.
    """
    try:
        review = get_access_review_for_reviewer(
            review_id,
            current_user.get_id())
    except ValueError:
        abort(404)
        
    return render_template(
        "access-review-detail.html", 
        review=review)

@bp_governance.route("/access-reviews/new", methods=["GET", "POST"])
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def create_access_review():
    """
    Allow access review managers to create an audited draft campaign.
    """

    if request.method == "GET":
        return render_template("access-review-create.html")

    name = request.form.get("name", "")
    reviewer_user_id = request.form.get("reviewer_user_id", "")
    due_at_raw = request.form.get("due_at", "").strip()

    due_at = None

    if due_at_raw:
        try:
            due_at = datetime.fromisoformat(due_at_raw)

            if due_at.tzinfo is not None:
                raise ValueError("unexpected_timezone")

            due_at = due_at.replace(tzinfo=timezone.utc)

        except ValueError:
            return render_template(
                "access-review-create.html",
                error="Enter a valid due date and time in UTC.",
            ), 400

    try:
        review = create_access_review_with_audit(
            name=name,
            created_by_user_id=current_user.get_id(),
            actor_username=current_user.username,
            reviewer_user_id=reviewer_user_id,
            admin_api_url= current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url= current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id= current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            due_at=due_at,
        )

    except ValueError:
        return render_template(
            "access-review-create.html",
            error="Enter a campaign name and a valid reviewer ID.",
        ), 400

    except (AuditPersistenceError, SQLAlchemyError) as exc:
        current_app.logger.exception(
            json.dumps({
                "event": "access_review.create",
                "outcome": "failure",
                "source": "governance-portal",
                "actor_user_id": current_user.get_id(),
                "error_type": type(exc).__name__,
            })
        )

        return render_template(
            "access-review-create.html",
            error="The campaign could not be saved. Please try again.",
        ), 500
    
    except KeycloakAdminAPIError: 
        return render_template(
            "access-review-create.html",
            error="The reviewer could not be verified. Please try again.",
        ), 503

    return redirect(
        url_for(
            "governance.manage_access_review_detail",
            review_id=review.id,
        ),
        303,
    )
    
@bp_governance.get("/access-reviews/manage")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def manage_access_reviews():
    """
    Display access review campaigns created by the authenticated manager.
    """

    reviews = get_access_reviews_for_manager(
        current_user.get_id()
    )

    return render_template(
        "access-reviews-manage.html",
        reviews=reviews,
    )
    
@bp_governance.get("/access-reviews/manage/<int:review_id>")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def manage_access_review_detail(review_id):
    """
    Display a campaign and its captured access to its access review manager.
    """

    try:
        campaign = get_access_review_for_manager(
            review_id,
            current_user.get_id(),
        )
    except ValueError:
        abort(404)

    return render_template(
        "access-review-detail.html",
        review=campaign,
        manager_view=True,
    )

    
    