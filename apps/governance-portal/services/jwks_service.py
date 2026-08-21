import threading
import time

import requests
from joserfc.jwk import KeySet


_JWKS_CACHE = {}
_JWKS_CACHE_LOCK = threading.Lock()


def _fetch_key_set(jwks_url):
    """
    Download Keycloak's current public signing keys.
    """

    response = requests.get(
        jwks_url,
        timeout=5,
    )

    response.raise_for_status()

    return KeySet.import_key_set(
        response.json()
    )


def get_key_set(
    jwks_url,
    ttl_seconds=300,
    force_refresh=False,
):
    """
    Return Keycloak's public signing keys.

    Cached keys are reused until their TTL expires.
    force_refresh=True ignores the cache and downloads
    the current keys from Keycloak.
    """

    now = time.monotonic()

    with _JWKS_CACHE_LOCK:
        cached = _JWKS_CACHE.get(jwks_url)

        if (
            cached is not None
            and not force_refresh
            and now - cached["fetched_at"] < ttl_seconds
        ):
            return cached["keyset"]

        key_set = _fetch_key_set(jwks_url)

        _JWKS_CACHE[jwks_url] = {
            "keyset": key_set,
            "fetched_at": time.monotonic(),
        }

        return key_set