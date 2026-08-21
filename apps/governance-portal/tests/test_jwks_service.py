import pytest

import services.jwks_service as jwks_service


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """
    Ensure tests never share cached JWKS state.
    """

    jwks_service._JWKS_CACHE.clear()

    yield

    jwks_service._JWKS_CACHE.clear()


def test_jwks_is_cached(monkeypatch):
    """
    Two requests inside the TTL should use the same
    cached KeySet and fetch Keycloak only once.
    """

    fake_keyset = object()

    calls = {
        "count": 0,
    }

    def fake_fetch(jwks_url):
        calls["count"] += 1
        return fake_keyset

    monkeypatch.setattr(
        jwks_service,
        "_fetch_key_set",
        fake_fetch,
    )

    url = "http://keycloak.test/certs"

    first = jwks_service.get_key_set(url)
    second = jwks_service.get_key_set(url)

    assert first is fake_keyset
    assert second is fake_keyset

    assert calls["count"] == 1


def test_force_refresh_bypasses_cache(
    monkeypatch,
):
    """
    force_refresh=True should download new signing
    keys even when cached keys are still valid.
    """

    keysets = [
        object(),
        object(),
    ]

    calls = {
        "count": 0,
    }

    def fake_fetch(jwks_url):
        result = keysets[calls["count"]]
        calls["count"] += 1
        return result

    monkeypatch.setattr(
        jwks_service,
        "_fetch_key_set",
        fake_fetch,
    )

    url = "http://keycloak.test/certs"

    first = jwks_service.get_key_set(url)

    second = jwks_service.get_key_set(
        url,
        force_refresh=True,
    )

    assert first is keysets[0]
    assert second is keysets[1]

    assert calls["count"] == 2


def test_expired_jwks_cache_is_refreshed(
    monkeypatch,
):
    """
    A JWKS cache entry older than its configured TTL
    should be replaced automatically.
    """

    first_keyset = object()
    refreshed_keyset = object()

    calls = {
        "count": 0,
    }

    def fake_fetch(jwks_url):
        calls["count"] += 1

        if calls["count"] == 1:
            return first_keyset

        return refreshed_keyset

    monkeypatch.setattr(
        jwks_service,
        "_fetch_key_set",
        fake_fetch,
    )

    url = "http://keycloak.test/certs"

    first = jwks_service.get_key_set(
        url,
        ttl_seconds=300,
    )

    # Artificially age the cache instead of
    # actually waiting five minutes.
    jwks_service._JWKS_CACHE[
        url
    ]["fetched_at"] -= 301

    second = jwks_service.get_key_set(
        url,
        ttl_seconds=300,
    )

    assert first is first_keyset
    assert second is refreshed_keyset

    assert calls["count"] == 2


def test_fetch_key_set_uses_http_timeout(
    monkeypatch,
):
    """
    JWKS retrieval must have a network timeout
    rather than potentially hanging indefinitely.
    """

    fake_keyset = object()

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "keys": [],
            }

    def fake_get(url, timeout):
        assert url == (
            "http://keycloak.test/certs"
        )

        assert timeout == 5

        return FakeResponse()

    monkeypatch.setattr(
        jwks_service.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        jwks_service.KeySet,
        "import_key_set",
        staticmethod(
            lambda data: fake_keyset
        ),
    )

    result = jwks_service._fetch_key_set(
        "http://keycloak.test/certs"
    )

    assert result is fake_keyset