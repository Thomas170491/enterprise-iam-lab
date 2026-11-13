from unittest.mock import Mock
import services.keycloak_auth_service as auth_service
from services.exceptions import KeycloakAdminAPIError
import requests
import pytest


def test_get_service_token(monkeypatch):

    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = {
        "access_token": "fake-service-token",
        "expires_in": 300,
        "token_type": "Bearer",
    }

    def fake_post(
        url,
        data,
        auth,
        timeout,
    ):
        assert url == "https://keycloak.test/token"

        assert data == {"grant_type": "client_credentials"}

        assert auth == (
            "iam-governance-service",
            "fake-secret",
        )

        assert timeout == 5

        return fake_response

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        fake_post,
    )

    token = auth_service.get_service_access_token(
        token_url="https://keycloak.test/token",
        client_id="iam-governance-service",
        client_secret="fake-secret",
    )

    assert token == "fake-service-token"


def test_service_authentication_failure(
    monkeypatch,
):
    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("Keycloak unavailable")

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        fake_post,
    )

    with pytest.raises(auth_service.KeycloakServiceAuthenticationError):
        auth_service.get_service_access_token(
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
        )


def test_missing_service_access_token(
    monkeypatch,
):
    fake_response = Mock()

    fake_response.raise_for_status.return_value = None

    fake_response.json.return_value = {"token_type": "Bearer"}

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        lambda *args, **kwargs: fake_response,
    )

    with pytest.raises(auth_service.KeycloakServiceAuthenticationError):
        auth_service.get_service_access_token(
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
        )


def test_service_authentication_error_is_a_keycloak_admin_api_error(monkeypatch):
    """
    Verify that a token request failure is raised as a Keycloak Admin API failure.
    """

    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("Keycloak unavailable")

    monkeypatch.setattr(auth_service.requests, "post", fake_post)

    with pytest.raises(KeycloakAdminAPIError):
        auth_service.get_service_access_token(
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
        )


@pytest.mark.parametrize(
    "json_behaviour",
    [
        {"side_effect": requests.exceptions.JSONDecodeError("not json", "<html>", 0)},
        {"side_effect": ValueError("not json")},
        {"return_value": ["access_token"]},
        {"return_value": None},
    ],
)
def test_invalid_service_token_response_body(monkeypatch, json_behaviour):
    """
    Verify that a non-JSON or non-object token response is an authentication failure.
    """
    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.configure_mock(**json_behaviour)

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        lambda *args, **kwargs: fake_response,
    )

    with pytest.raises(auth_service.KeycloakServiceAuthenticationError):
        auth_service.get_service_access_token(
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
        )
