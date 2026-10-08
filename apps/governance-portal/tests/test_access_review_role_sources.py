from unittest.mock import Mock
import services.access_review_service as access_review_service


def test_resolve_user_client_role_sources_inherits_parent_group_role(monkeypatch):
    """
    Verify that a role inherited through a child membership is attributed to its granting parent group.
    """

    child_group = {
        "id": "finance-team-id",
        "name": "Finance Team",
        "parentId": "finance-id",
    }
    parent_group = {
        "id": "finance-id",
        "name": "Finance",
        "parentId": None,
    }
    role = {
        "id": "finance-role-id",
        "name": "finance-data-viewer",
    }

    direct_roles = []
    effective_roles = [role]

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(return_value=direct_roles),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        Mock(return_value=effective_roles),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_user_groups",
        Mock(return_value=[child_group]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_ancestors",
        Mock(return_value=[parent_group]),
    )

    def fake_get_group_role_mappings(**kwargs):
        """
        Return Finance's direct role mapping and no mapping for Finance Team.
        """
        group_id = kwargs["group_id"]

        if group_id == "finance-id":
            return {"clientMappings": {"employee-portal": {"mappings": [role]}}}

        if group_id == "finance-team-id":
            return {"clientMappings": {}}

        raise AssertionError(f"Unexpected group ID: {group_id}")

    monkeypatch.setattr(
        access_review_service,
        "get_group_role_mappings",
        fake_get_group_role_mappings,
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-role-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "inherited",
            "grant_sources": [
                {
                    "type": "group",
                    "group_id": "finance-id",
                    "membership_group_id": "finance-team-id",
                    "assigned_role_id": "finance-role-id",
                    "composite_path": [],
                }
            ],
        }
    ]


def test_resolve_user_client_role_sources_handles_direct_role_without_groups(
    monkeypatch,
):
    """
    Verify that a direct user role is resolved when the user belongs to no groups.
    """

    role = {
        "id": "finance-role-id",
        "name": "finance-data-viewer",
    }

    fake_get_group_ancestors = Mock()
    fake_get_group_role_mappings = Mock()

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(return_value=[role]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        Mock(return_value=[role]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_user_groups",
        Mock(return_value=[]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_ancestors",
        fake_get_group_ancestors,
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_role_mappings",
        fake_get_group_role_mappings,
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-role-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "direct",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-role-id",
                    "composite_path": [],
                }
            ],
        }
    ]
    fake_get_group_ancestors.assert_not_called()
    fake_get_group_role_mappings.assert_not_called()


def test_resolve_user_client_role_sources_reports_both_direct_and_group_grants(
    monkeypatch,
):
    """
    Verify that a role granted directly and through a group reports both sources.
    """

    role = {
        "id": "finance-role-id",
        "name": "finance-data-viewer",
    }
    finance_group = {
        "id": "finance-id",
        "name": "Finance",
        "parentId": None,
    }

    fake_get_group_ancestors = Mock(return_value=[])

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        Mock(return_value=[role]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        Mock(return_value=[role]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_user_groups",
        Mock(return_value=[finance_group]),
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_ancestors",
        fake_get_group_ancestors,
    )
    fake_get_group_role_mappings = Mock(
        return_value={
            "clientMappings": {
                "employee-portal": {"mappings": [role]},
            }
        }
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_role_mappings",
        fake_get_group_role_mappings,
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-role-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "both",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-role-id",
                    "composite_path": [],
                },
                {
                    "type": "group",
                    "group_id": "finance-id",
                    "membership_group_id": "finance-id",
                    "assigned_role_id": "finance-role-id",
                    "composite_path": [],
                },
            ],
        }
    ]
    fake_get_group_ancestors.assert_called_once()
    fake_get_group_role_mappings.assert_called_once()


def test_resolve_user_client_role_sources_traces_parent_group_composite(monkeypatch):
    """
    Verify that a parent group's composite grant identifies the effective role's path.
    """

    child_group = {
        "id": "finance-team-id",
        "name": "Finance Team",
        "parentId": "finance-id",
    }
    parent_group = {
        "id": "finance-id",
        "name": "Finance",
        "parentId": None,
    }
    assigned_role = {
        "id": "finance-staff-id",
        "name": "finance-staff",
        "composite": True,
    }
    effective_role = {"id": "finance-viewer-id", "name": "finance-data-viewer"}

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        lambda **kwargs: [effective_role],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_user_groups",
        lambda **kwargs: [child_group],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_group_ancestors",
        Mock(return_value=[parent_group]),
    )

    def fake_get_group_role_mappings(**kwargs):
        """
        Return Finance's assigned role and no assigned roles for Finance Team.
        """
        if kwargs["group_id"] == "finance-id":
            return {
                "clientMappings": {
                    "employee-portal": {"mappings": [assigned_role]},
                }
            }

        assert kwargs["group_id"] == "finance-team-id"
        return {"clientMappings": {}}

    monkeypatch.setattr(
        access_review_service,
        "get_group_role_mappings",
        fake_get_group_role_mappings,
    )

    composite_children_by_role_id = {
        assigned_role["id"]: [effective_role],
        effective_role["id"]: [],
    }

    def fake_get_role_composite_children(**kwargs):
        """
        Return the direct child roles for the requested role ID.
        """
        role_id = kwargs["role_id"]
        assert role_id in composite_children_by_role_id
        return composite_children_by_role_id[role_id]

    monkeypatch.setattr(
        access_review_service,
        "get_role_composite_children",
        fake_get_role_composite_children,
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-viewer-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "inherited",
            "grant_sources": [
                {
                    "type": "group",
                    "group_id": "finance-id",
                    "membership_group_id": "finance-team-id",
                    "assigned_role_id": "finance-staff-id",
                    "composite_path": ["finance-staff-id", "finance-viewer-id"],
                }
            ],
        }
    ]


def test_resolve_user_client_role_sources_traces_direct_user_composite(monkeypatch):
    """
    Verify that a directly assigned composite explains an effective user role.
    """

    assigned_role = {
        "id": "finance-staff-id",
        "name": "finance-staff",
        "composite": True,
    }
    effective_role = {
        "id": "finance-viewer-id",
        "name": "finance-data-viewer",
    }

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        lambda **kwargs: [assigned_role],
    )
    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        lambda **kwargs: [effective_role],
    )
    monkeypatch.setattr(access_review_service, "get_user_groups", lambda **kwargs: [])
    monkeypatch.setattr(
        access_review_service,
        "get_role_composite_children",
        lambda **kwargs: (
            [effective_role] if kwargs["role_id"] == assigned_role["id"] else []
        ),
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-viewer-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "direct",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-staff-id",
                    "composite_path": [
                        "finance-staff-id",
                        "finance-viewer-id",
                    ],
                }
            ],
        }
    ]


def test_resolve_user_client_role_sources_traces_nested_direct_user_composite(
    monkeypatch,
):
    """
    Verify that a direct user grant traces through nested composite roles.
    """

    assigned_role = {
        "id": "finance-staff-id",
        "name": "finance-staff",
        "composite": True,
    }
    middle_role = {
        "id": "finance-reader-id",
        "name": "finance-reader",
        "composite": True,
    }
    effective_role = {
        "id": "finance-viewer-id",
        "name": "finance-data-viewer",
    }

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        lambda **kwargs: [assigned_role],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        lambda **kwargs: [effective_role],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_role_composite_children",
        lambda **kwargs: (
            [middle_role]
            if kwargs["role_id"] == assigned_role["id"]
            else [effective_role] if kwargs["role_id"] == middle_role["id"] else []
        ),
    )

    monkeypatch.setattr(access_review_service, "get_user_groups", lambda **kwargs: [])

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-viewer-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "direct",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-staff-id",
                    "composite_path": [
                        "finance-staff-id",
                        "finance-reader-id",
                        "finance-viewer-id",
                    ],
                }
            ],
        }
    ]


def test_resolve_user_client_role_sources_preserves_multiple_direct_composite_grants(
    monkeypatch,
):
    """
    Verify that two assigned composites retain both sources for one effective role.
    """

    assigned_role1 = {
        "id": "finance-staff-id",
        "name": "finance-staff",
        "composite": True,
    }
    assigned_role2 = {
        "id": "finance-manager-id",
        "name": "finance-manager",
        "composite": True,
    }
    middle_role = {
        "id": "finance-reader-id",
        "name": "finance-reader",
        "composite": True,
    }
    effective_role = {
        "id": "finance-viewer-id",
        "name": "finance-data-viewer",
    }

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        lambda **kwargs: [assigned_role1, assigned_role2],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        lambda **kwargs: [effective_role],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_role_composite_children",
        lambda **kwargs: (
            [middle_role]
            if kwargs["role_id"] == assigned_role1["id"]
            or kwargs["role_id"] == assigned_role2["id"]
            else [effective_role] if kwargs["role_id"] == middle_role["id"] else []
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_user_groups",
        lambda **kwargs: [],
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-viewer-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "direct",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-staff-id",
                    "composite_path": [
                        "finance-staff-id",
                        "finance-reader-id",
                        "finance-viewer-id",
                    ],
                },
                {
                    "type": "user",
                    "user_id": "user-123",
                    ("assigned_role_id"): ("finance-manager-id"),
                    ("composite_path"): (
                        [
                            "finance-manager-id",
                            "finance-reader-id",
                            "finance-viewer-id",
                        ]
                    ),
                },
            ],
        }
    ]


def test_resolve_user_client_role_sources_reports_both_composite_user_and_group_grants(
    monkeypatch,
):
    """
    Verify that user-composite and group grants both explain one effective role.
    """

    effective_role = {
        "id": "finance-viewer-id",
        "name": "finance-data-viewer",
    }

    assigned_role = {
        "id": "finance-staff-id",
        "name": "finance-staff",
        "composite": True,
    }

    finance_group = {
        "id": "finance-id",
        "name": "Finance",
        "parentId": None,
    }

    monkeypatch.setattr(
        access_review_service,
        "get_direct_client_roles",
        lambda **kwargs: [assigned_role],
    )

    monkeypatch.setattr(
        access_review_service,
        "get_effective_client_roles",
        lambda **kwargs: [effective_role],
    )

    monkeypatch.setattr(
        access_review_service, "get_user_groups", lambda **kwargs: [finance_group]
    )

    monkeypatch.setattr(
        access_review_service,
        "get_role_composite_children",
        lambda **kwargs: (
            [effective_role] if kwargs["role_id"] == assigned_role["id"] else []
        ),
    )

    monkeypatch.setattr(
        access_review_service,
        "get_group_ancestors",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        access_review_service,
        "get_group_role_mappings",
        lambda **kwargs: {
            "clientMappings": {
                "employee-portal": {
                    "mappings": [effective_role],
                }
            }
        },
    )

    resolved = access_review_service.resolve_user_client_role_sources(
        admin_api_url="https://keycloak.test/admin/realms/novasecure",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        user_id="user-123",
        target_client_name="employee-portal",
    )

    assert resolved == [
        {
            "role_id": "finance-viewer-id",
            "role_name": "finance-data-viewer",
            "assignment_source": "both",
            "grant_sources": [
                {
                    "type": "user",
                    "user_id": "user-123",
                    "assigned_role_id": "finance-staff-id",
                    "composite_path": [
                        "finance-staff-id",
                        "finance-viewer-id",
                    ],
                },
                {
                    "group_id": "finance-id",
                    "membership_group_id": "finance-id",
                    "type": "group",
                    "assigned_role_id": "finance-viewer-id",
                    "composite_path": [],
                },
            ],
        }
    ]
