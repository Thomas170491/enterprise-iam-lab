import json 
from typing import Any

from models import AccessReviewItem

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