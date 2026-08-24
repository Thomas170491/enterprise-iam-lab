from unittest.mock import Mock
import services.keycloak_auth_service as auth_service
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

        assert data == {
            "grant_type": "client_credentials"
        }

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
        raise requests.ConnectionError(
            "Keycloak unavailable"
        )

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        fake_post,
    )

    with pytest.raises(
        auth_service.KeycloakServiceAuthenticationError
    ):
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

    fake_response.json.return_value = {
        "token_type": "Bearer"
    }

    monkeypatch.setattr(
        auth_service.requests,
        "post",
        lambda *args, **kwargs: fake_response,
    )

    with pytest.raises(
        auth_service.KeycloakServiceAuthenticationError
    ):
        auth_service.get_service_access_token(
            token_url="https://keycloak.test/token",
            client_id="iam-governance-service",
            client_secret="fake-secret",
        )