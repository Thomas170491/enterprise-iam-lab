from auth.permissions import (
    ACCESS_REVIEWER,
    AUDIT_LOG_VIEWER,
    IAM_DASHBOARD_ACCESS,
    IDENTITY_MANAGER,
    IDENTITY_VIEWER,
    REPORT_EXPORTER,
    ROLE_MANAGER,
)

def test_gouvernance_permission_names():
    assert IAM_DASHBOARD_ACCESS == (
        "iam-dashboard-access"
    )

    assert IDENTITY_VIEWER == (
        "identity-viewer"
    )

    assert IDENTITY_MANAGER == (
        "identity-manager"
    )

    assert ROLE_MANAGER == (
        "role-manager"
    )

    assert ACCESS_REVIEWER == (
        "access-reviewer"
    )

    assert AUDIT_LOG_VIEWER == (
        "audit-log-viewer"
    )

    assert REPORT_EXPORTER == (
        "report-exporter"
    )