import json
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from auth.decorators import client_role_required
from auth.permissions import (
    ACCESS_REVIEW_MANAGER,
    ACCESS_REVIEWER,
    AUDIT_LOG_REVIEWER,
    IAM_DASHBOARD_ACCESS,
    IDENTITY_VIEWER,
    ROLE_MANAGER,
)
from services.access_review_service import (
    create_access_review_with_audit,
    get_access_review_for_manager,
    get_access_review_for_reviewer,
    get_access_reviews_for_manager,
    get_access_reviews_for_reviewer,
    populate_access_review_with_audit,
    open_access_review_with_audit,
    cancel_access_review_with_audit
)
from services.audit_service import (
    get_recent_audit_events,
    record_audit_event,
)
from services.exceptions import (
    AuditPersistenceError,
    AuditQueryError,
    KeycloakAdminAPIError,
    RoleAdministrationPolicyError,
)
from services.identity_service import (
    get_identity_access,
    search_identities,
)
from services.role_service import (
    assign_identity_client_role,
    get_managed_roles,
    remove_identity_client_role,
)

bp_governance = Blueprint(
    "governance",
    __name__,
)


def _log_governance_event(
    level,
    event,
    outcome,
    reason,
    exc=None,
    **context,
):
    """
    Log a structured governance event without including exception messages or secrets.
    """
    payload = {
        "event": event,
        "outcome": outcome,
        "source": "governance-portal",
        "actor_user_id": current_user.get_id(),
        "reason": reason,
    }

    if exc is not None:
        payload["error_type"] = type(exc).__name__

    payload.update(context)

    current_app.logger.log(
        level,
        json.dumps(payload),
    )


@bp_governance.get("/")
@login_required
@client_role_required(IAM_DASHBOARD_ACCESS)
def dashboard():
    """
    Render the Governance Portal dashboard.
    """
    return render_template("dashboard.html")


@bp_governance.get("/identities")
@login_required
@client_role_required(IDENTITY_VIEWER)
def identities():
    """
    Search realm identities and display the matching results.
    """
    search = request.args.get(
        "search",
        default="",
        type=str,
    ).strip()

    has_searched = "search" in request.args
    identities = []

    if has_searched:
        identities = search_identities(
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
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
    """
    Display an identity's effective access and audit the successful view.
    """
    try:
        identity_access = get_identity_access(
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            user_id=user_id,
            target_client_name="employee-portal",
        )

        direct_role_names = {
            role["name"] for role in identity_access["direct_client_roles"]
        }

        managed_roles = get_managed_roles("employee-portal")

    except KeycloakAdminAPIError as exc:
        _log_governance_event(
            level=40,
            event="identity.view",
            outcome="failure",
            reason="identity_access_retrieval_failed",
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
        )

        return render_template("identity-detail-error.html"), 502

    try:
        record_audit_event(
            actor_user_id=current_user.get_id(),
            actor_username=current_user.username,
            action="identity.view",
            target_type="identity",
            target_id=user_id,
            target_name=identity_access["identity"].get("username"),
            outcome="success",
            details={
                "source": "governance-portal",
                "service_client": current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            },
        )

    except AuditPersistenceError as exc:
        _log_governance_event(
            level=40,
            event="audit.persist",
            outcome="failure",
            reason="identity_view_audit_failed",
            exc=exc,
            target_id=user_id,
            audited_action="identity.view",
        )

    return render_template(
        "identity_detail.html",
        identity_access=identity_access,
        direct_role_names=direct_role_names,
        managed_roles=managed_roles,
    )


@bp_governance.get("/audit")
@login_required
@client_role_required(AUDIT_LOG_REVIEWER)
def audit_log():
    """
    Display recent audit events to an authorized audit reviewer.
    """
    try:
        events = get_recent_audit_events(limit=100)

    except AuditQueryError as exc:
        _log_governance_event(
            level=40,
            event="audit.query",
            outcome="failure",
            reason="audit_query_failed",
            exc=exc,
        )

        return render_template("audit-log-error.html"), 503

    return render_template(
        "audit-log.html",
        events=events,
    )


@bp_governance.post("/identities/<user_id>/roles")
@login_required
@client_role_required(ROLE_MANAGER)
def assign_identity_role(user_id):
    """
    Assign an Employee Portal role through the governed role service.
    """
    role_name = request.form.get("role_name", "").strip()

    if not role_name:
        abort(400)

    try:
        assign_identity_client_role(
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            user_id=user_id,
            target_client_name="employee-portal",
            role_name=role_name,
            actor_user_id=current_user.get_id(),
            actor_username=current_user.username,
        )

    except RoleAdministrationPolicyError as exc:
        _log_governance_event(
            level=30,
            event="role.assign",
            outcome="denied",
            reason=exc.reason,
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        sod_messages = {
            "sod_deny": (
                "This role combination violates a segregation-of-duties rule. "
                "No role was assigned."
            ),
            "sod_requires_review": (
                "This role assignment requires review. " "No role was assigned."
            ),
        }

        if exc.reason in sod_messages:
            return (
                render_template(
                    "role-assignment-blocked.html",
                    message=sod_messages[exc.reason],
                ),
                403,
            )

        abort(403)

    except AuditPersistenceError as exc:
        _log_governance_event(
            level=40,
            event="role.assign",
            outcome="failure",
            reason="required_audit_persistence_failed",
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        abort(503)

    except KeycloakAdminAPIError as exc:
        _log_governance_event(
            level=40,
            event="role.assign",
            outcome="failure",
            reason="keycloak_role_assignment_failed",
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        abort(502)

    return redirect(
        url_for(
            "governance.identity_detail",
            user_id=user_id,
        )
    )


@bp_governance.post("/identities/<user_id>/roles/<role_name>/remove")
@login_required
@client_role_required(ROLE_MANAGER)
def remove_identity_role(user_id, role_name):
    """
    Remove an Employee Portal role through the governed role service.
    """
    role_name = role_name.strip()

    if not role_name:
        abort(400)

    try:
        remove_identity_client_role(
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            user_id=user_id,
            target_client_name="employee-portal",
            role_name=role_name,
            actor_user_id=current_user.get_id(),
            actor_username=current_user.username,
        )

    except RoleAdministrationPolicyError as exc:
        _log_governance_event(
            level=30,
            event="role.remove",
            outcome="denied",
            reason=exc.reason,
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        abort(403)

    except AuditPersistenceError as exc:
        _log_governance_event(
            level=40,
            event="role.remove",
            outcome="failure",
            reason="required_audit_persistence_failed",
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        abort(503)

    except KeycloakAdminAPIError as exc:
        _log_governance_event(
            level=40,
            event="role.remove",
            outcome="failure",
            reason="keycloak_role_removal_failed",
            exc=exc,
            target_id=user_id,
            client_name="employee-portal",
            role_name=role_name,
        )

        abort(502)

    return redirect(
        url_for(
            "governance.identity_detail",
            user_id=user_id,
        )
    )


@bp_governance.get("/access-reviews")
@login_required
@client_role_required(ACCESS_REVIEWER)
def access_reviews():
    """
    Display campaigns assigned to the authenticated reviewer.
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
            current_user.get_id(),
        )

    except ValueError:
        abort(404)

    return render_template(
        "access-review-detail.html",
        review=review,
    )


@bp_governance.route("/access-reviews/new", methods=["GET", "POST"])
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def create_access_review():
    """
    Allow managers to create an audited draft campaign with an eligible reviewer.
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
            return (
                render_template(
                    "access-review-create.html",
                    error="Enter a valid due date and time in UTC.",
                ),
                400,
            )

    try:
        review = create_access_review_with_audit(
            name=name,
            created_by_user_id=current_user.get_id(),
            actor_username=current_user.username,
            reviewer_user_id=reviewer_user_id,
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            due_at=due_at,
        )

    except ValueError as exc:
        reason = str(exc)

        if reason in (
            "reviewer_not_enabled",
            "reviewer_missing_required_role",
        ):
            _log_governance_event(
                level=30,
                event="access_review.create",
                outcome="denied",
                reason=reason,
            )

        return (
            render_template(
                "access-review-create.html",
                error="Enter a campaign name and a valid reviewer ID.",
            ),
            400,
        )

    except (AuditPersistenceError, SQLAlchemyError) as exc:
        _log_governance_event(
            level=40,
            event="access_review.create",
            outcome="failure",
            reason="campaign_persistence_failed",
            exc=exc,
        )

        return (
            render_template(
                "access-review-create.html",
                error="The campaign could not be saved. Please try again.",
            ),
            500,
        )

    except KeycloakAdminAPIError as exc:
        _log_governance_event(
            level=40,
            event="access_review.create",
            outcome="failure",
            reason="reviewer_verification_failed",
            exc=exc,
        )

        return (
            render_template(
                "access-review-create.html",
                error="The reviewer could not be verified. Please try again.",
            ),
            503,
        )

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
    Display campaigns created by the authenticated access review manager.
    """
    reviews = get_access_reviews_for_manager(current_user.get_id())

    return render_template(
        "access-reviews-manage.html",
        reviews=reviews,
    )


@bp_governance.get("/access-reviews/manage/<int:review_id>")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def manage_access_review_detail(review_id):
    """
    Display a campaign and its captured access to the manager who created it.
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


@bp_governance.post("/access-reviews/manage/<int:review_id>/populate")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def populate_access_review(review_id):
    """
    Capture an identity's managed direct access in a campaign owned by the current manager.
    """

    user_id = request.form.get("user_id", "").strip()

    try:
        populate_access_review_with_audit(
            review_id=review_id,
            manager_user_id=current_user.get_id(),
            user_id=user_id,
            admin_api_url=current_app.config["KEYCLOAK_ADMIN_API_URL"],
            token_url=current_app.config["KEYCLOAK_TOKEN_URL"],
            client_id=current_app.config["KEYCLOAK_SERVICE_CLIENT_ID"],
            client_secret=current_app.config["KEYCLOAK_SERVICE_CLIENT_SECRET"],
            actor_username=current_user.username,
        )

    except ValueError as exc:
        if str(exc) == "access_review_not_found":
            _log_governance_event(
                event="access_review.populate",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )

            abort(404)

        elif str(exc) == "access_review_not_draft":
            _log_governance_event(
                event="access_review.populate",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )
            abort(409)

        else:
            abort(400)

    except KeycloakAdminAPIError as exc:
        _log_governance_event(
            level=40,
            event="access_review.populate",
            outcome="failure",
            reason="identity_access_retrieval_failed",
            exc=exc,
            target_id=str(review_id),
        )
        abort(503)

    except (AuditPersistenceError, SQLAlchemyError) as exc:
        _log_governance_event(
            level=40,
            event="access_review.populate",
            outcome="failure",
            reason="population_persistence_failed",
            exc=exc,
            target_id=str(review_id),
        )
        abort(503)

    return redirect(
        url_for(
            "governance.manage_access_review_detail",
            review_id=review_id,
        ),
        303,
    )

@bp_governance.post("/access-reviews/manage/<int:review_id>/open")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def open_access_review(review_id):
    """
    Open a campaign owned by the authenticated manager and audit the transition.
    """
    try:
        open_access_review_with_audit(
            review_id= review_id,
            manager_user_id=current_user.get_id(),
            actor_username=current_user.username
        )
    except ValueError as exc :
        if str(exc) == "access_review_not_found" :
            _log_governance_event(
                event="access_review.open",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )
            abort(404)

        if str(exc) in ("access_review_not_draft","access_review_empty"):
            _log_governance_event(
                event="access_review.open",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )
            abort(409)

        else:
            abort(400)
    
    except (AuditPersistenceError, SQLAlchemyError) as exc :
        _log_governance_event(
            level=40,
            event="access_review.open",
            outcome="failure",
            reason="campaign_open_persistence_failed",
            exc=exc,
            target_id=str(review_id),
        )
        abort(503)
    
    return redirect(
        url_for(
            "governance.manage_access_review_detail",
            review_id = review_id
        ),
        303,
    )

@bp_governance.post("/access-reviews/manage/<int:review_id>/cancel")
@login_required
@client_role_required(ACCESS_REVIEW_MANAGER)
def cancel_access_review(review_id):
    """
    Cancel a campaign owned by the authenticated manager and audit the transition.
    """
    try:
        cancel_access_review_with_audit(
            review_id= review_id,
            manager_user_id=current_user.get_id(),
            actor_username=current_user.username
        )
    except ValueError as exc :
        if str(exc) == "access_review_not_found" :
            _log_governance_event(
                event="access_review.cancel",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )
            abort(404)

        if str(exc) == "access_review_not_cancellable":
            _log_governance_event(
                event="access_review.cancel",
                outcome="denied",
                level=30,
                reason=str(exc),
                target_id=str(review_id),
            )
            abort(409)

        else:
            abort(400)
    
    except (AuditPersistenceError, SQLAlchemyError) as exc :
        _log_governance_event(
            level=40,
            event="access_review.cancel",
            outcome="failure",
            reason="campaign_cancel_persistence_failed",
            exc=exc,
            target_id=str(review_id),
        )
        abort(503)
    
    return redirect(
        url_for(
            "governance.manage_access_review_detail",
            review_id = review_id
        ),
        303,
    )        
    
    