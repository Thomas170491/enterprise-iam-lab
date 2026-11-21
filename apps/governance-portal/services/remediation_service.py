import json 
from typing import Any

from models import AccessReviewItem
from services.access_review_service import resolve_user_client_role_sources 

def assess_live_access(item: AccessReviewItem, live_roles: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compare a captured item with live role evidence and report what removing its direct role would do.

    drift is "none" when the live grants equal the captured ones (in any order),
    "role_removed" when the role is no longer effective, and "sources_changed" otherwise.
    direct_grant_present is true when a user grant maps exactly this role, so removing
    the user's direct role mapping removes that grant. other_grants_present is true when
    any live grant would survive that removal (a group grant or a composite path).
    """
    
    live_role = next(
        (role for role in live_roles if role["role_id"] == item.role_id), None
    )
    
    if live_role is None :
        return {
            "drift": "role_removed",
            "direct_grant_present": False,
            "other_grants_present": False,
        }
        
    live_grants = live_role["grant_sources"]
    
    captured  = {json.dumps(grant, sort_keys=True) for grant in item.grant_sources}
    live      = {json.dumps(grant, sort_keys=True) for grant in live_grants}

    direct = [
        grant
        for grant in live_grants
        if grant["type"] == "user" and grant["assigned_role_id"] == item.role_id
    ]

    return {
        "drift": "none" if captured == live else "sources_changed",
        "direct_grant_present": bool(direct),
        "other_grants_present": len(direct) < len(live_grants),
    }
    
def get_live_access_assessment(
    item: AccessReviewItem,
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """
    Read the item's role from Keycloak and assess it against the captured evidence.

    Only the item's own role is traced, so an untraceable unrelated role cannot block it.
    Keycloak failures and role_source_untraceable propagate: remediation must not act on them.
    """
    live_roles = resolve_user_client_role_sources(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=item.user_id,
        target_client_name="employee-portal",
        role_ids={item.role_id},
    )

    return assess_live_access(item, live_roles)
