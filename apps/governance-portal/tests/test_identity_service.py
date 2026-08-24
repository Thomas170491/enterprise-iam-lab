import services.identity_service as identity_service


def test_search_identities_normalizes_keycloak_users(
    monkeypatch,
):
    """
    Verify that raw Keycloak user data is converted
    into the Governance Portal identity format.
    """

    fake_users = [
        {
            "id": "keycloak-user-123",
            "username": "e1004",
            "firstName": "Leo",
            "lastName": "Bernard",
            "email": "leo@example.test",
            "enabled": True,
            "attributes": {
                "employee_id": ["e1004"],
                "employment_status": ["active"],
                "job_title": ["IAM Operator"],
                "risk_level": ["high"],
            },
        }
    ]

    def fake_search_users(**kwargs):

        assert kwargs["search"] == "e1004"
        assert kwargs["max_results"] == 20

        return fake_users

    monkeypatch.setattr(
        identity_service,
        "search_users",
        fake_search_users,
    )

    identities = identity_service.search_identities(
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
        search="e1004",
    )

    assert len(identities) == 1

    identity = identities[0]

    assert identity["id"] == "keycloak-user-123"
    assert identity["username"] == "e1004"
    assert identity["first_name"] == "Leo"
    assert identity["last_name"] == "Bernard"
    assert identity["employee_id"] == "e1004"
    assert identity["employment_status"] == "active"
    assert identity["job_title"] == "IAM Operator"
    assert identity["risk_level"] == "high"
    assert identity["enabled"] is True

def test_search_identities_handles_missing_attributes(
    monkeypatch,
):
    """
    Missing optional Keycloak attributes should not
    crash the Governance Portal.
    """

    fake_users = [
        {
            "id": "user-456",
            "username": "e1001",
            "firstName": "Alice",
            "lastName": "Martin",
            "enabled": True,
        }
    ]

    monkeypatch.setattr(
        identity_service,
        "search_users",
        lambda **kwargs: fake_users,
    )

    identities = identity_service.search_identities(
        admin_api_url="https://keycloak.test/admin",
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
    )

    identity = identities[0]

    assert identity["employee_id"] is None
    assert identity["employment_status"] is None
    assert identity["job_title"] is None
    assert identity["risk_level"] is None 