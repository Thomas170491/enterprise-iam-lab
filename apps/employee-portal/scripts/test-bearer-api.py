import getpass
import sys

import base64
import json

import requests


KEYCLOAK_URL = "http://localhost:8080"
REALM = "novasecure"

CLIENT_ID = "employee-portal-cli-test"
USERNAME = "e1002"

API_URL = "http://localhost:5000/api/v1"




def inspect_access_token(access_token):
    """
    Decode JWT payload for diagnostics only.

    IMPORTANT:
    This does NOT verify the signature.
    Never use this function for authorization decisions.
    """

    try:
        payload = access_token.split(".")[1]

        payload += "=" * (-len(payload) % 4)

        claims = json.loads(
            base64.urlsafe_b64decode(payload)
        )

    except (IndexError, ValueError, json.JSONDecodeError):
        print("FAIL: Could not inspect JWT payload.")
        return

    print()
    print("JWT diagnostics")
    print("-" * 30)
    print("iss:", claims.get("iss"))
    print("aud:", claims.get("aud"))
    print("azp:", claims.get("azp"))
    print("sub:", claims.get("sub"))

    resource_access = claims.get(
        "resource_access",
        {}
    )

    print(
        "resource_access clients:",
        list(resource_access.keys()),
    )
def get_access_token():
    password = getpass.getpass(
        "Marc Keycloak password: "
    )

    token_url = (
        f"{KEYCLOAK_URL}/realms/{REALM}"
        "/protocol/openid-connect/token"
    )

    try:
        response = requests.post(
            token_url,
            data={
                "client_id": CLIENT_ID,
                "username": USERNAME,
                "password": password,
                "grant_type": "password",
                "scope": "openid profile email",
            },
            timeout=5,
        )

    except requests.RequestException as exc:
        print(
            f"FAIL: Could not contact Keycloak: {exc}"
        )
        return None

    if response.status_code != 200:
        print(
            f"FAIL: Keycloak returned HTTP "
            f"{response.status_code}"
        )

        try:
            error_data = response.json()

            print(
                "Error:",
                error_data.get("error", "unknown"),
            )

            print(
                "Description:",
                error_data.get(
                    "error_description",
                    "No description provided",
                ),
            )

        except ValueError:
            print("Response:", response.text)

        return None

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        print("FAIL: Keycloak returned no access token.")
        return None

    print("PASS: Access token obtained.")

    inspect_access_token(access_token)


    return access_token

def test_bearer_endpoint(
    access_token,
    endpoint,
    expected_status=200,
):
    try:
        response = requests.get(
            f"{API_URL}/{endpoint}",
            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },
            timeout=5,
        )

    except requests.RequestException as exc:
        print(
            f"FAIL: /{endpoint} request failed: {exc}"
        )
        return False

    if response.status_code == expected_status:
        print(
            f"PASS: /{endpoint}"
            f" -> HTTP {response.status_code}"
        )
        return True

    print(
        f"FAIL: /{endpoint}"
        f" -> HTTP {response.status_code}"
        f" (expected {expected_status})"
    )

    try:
        print("Response:", response.json())
    except ValueError:
        print("Response:", response.text)

    return False


def test_missing_authentication():
    try:
        response = requests.get(
            f"{API_URL}/me",
            timeout=5,
        )

    except requests.RequestException as exc:
        print(
            f"FAIL: Missing-auth test failed: {exc}"
        )
        return False

    if response.status_code == 401:
        print(
            "PASS: Missing authentication -> HTTP 401"
        )
        return True

    print(
        "FAIL: Missing authentication"
        f" -> HTTP {response.status_code}"
    )

    return False


def test_malformed_authorization_header():
    try:
        response = requests.get(
            f"{API_URL}/me",
            headers={
                "Authorization": "Bearer"
            },
            timeout=5,
        )

    except requests.RequestException as exc:
        print(
            f"FAIL: Malformed-header test failed: {exc}"
        )
        return False

    if response.status_code == 401:
        print(
            "PASS: Malformed Bearer header -> HTTP 401"
        )
        return True

    print(
        "FAIL: Malformed Bearer header"
        f" -> HTTP {response.status_code}"
    )

    return False


def test_invalid_token():
    try:
        response = requests.get(
            f"{API_URL}/me",
            headers={
                "Authorization":
                    "Bearer definitely-not-a-jwt"
            },
            timeout=5,
        )

    except requests.RequestException as exc:
        print(
            f"FAIL: Invalid-token test failed: {exc}"
        )
        return False

    if response.status_code == 401:
        print(
            "PASS: Invalid Bearer token -> HTTP 401"
        )
        return True

    print(
        "FAIL: Invalid Bearer token"
        f" -> HTTP {response.status_code}"
    )

    return False


def main():
    print()
    print("NovaSecure Bearer API Integration Test")
    print("=" * 38)

    access_token = get_access_token()

    if access_token is None:
        sys.exit(1)

    print()
    print("Authenticated Bearer tests")
    print("-" * 30)

    results = [
        test_bearer_endpoint(
            access_token,
            "me",
        ),
        test_bearer_endpoint(
            access_token,
            "access",
        ),
        test_bearer_endpoint(
            access_token,
            "department",
        ),
    ]

    print()
    print("Authentication failure tests")
    print("-" * 30)

    results.extend([
        test_missing_authentication(),
        test_malformed_authorization_header(),
        test_invalid_token(),
    ])

    passed = sum(results)
    total = len(results)

    print()
    print("=" * 38)
    print(f"Result: {passed}/{total} tests passed")

    if all(results):
        print("PASS: Bearer API integration works.")
        sys.exit(0)

    print("FAIL: One or more tests failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()