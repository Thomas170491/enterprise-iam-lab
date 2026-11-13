"""
Shared helpers for the access review route tests.
"""
from html.parser import HTMLParser
from urllib.parse import urlsplit


class _CSRFFormParser(HTMLParser):
    """
    Extract a CSRF token from the form targeting the specified action path.
    """

    def __init__(self, action_path):
        """
        Initialize the target form path and captured token.
        """
        super().__init__()
        self.action_path = action_path
        self.in_target_form = False
        self.csrf_token = None

    def handle_starttag(self, tag, attrs):
        """
        Capture the CSRF input belonging to the target form.
        """
        attributes = dict(attrs)
        if tag == "form":
            action = attributes.get("action") or self.action_path
            self.in_target_form = urlsplit(action).path == self.action_path
        elif tag == "input" and self.in_target_form:
            if attributes.get("name") == "csrf_token":
                self.csrf_token = attributes.get("value")

    def handle_endtag(self, tag):
        """
        Stop capturing inputs when the current form ends.
        """
        if tag == "form":
            self.in_target_form = False


def _login_user(client, client_roles):
    """
    Authenticate a test user with the specified client roles.
    """
    with client.session_transaction() as session:
        session["user"] = {
            "sub": "test-subject",
            "username": "test-user",
            "name": "Test User",
            "email": "test@example.test",
            "client_roles": client_roles,
            "realm_roles": [],
        }
        session["_user_id"] = "test-subject"
        session["_fresh"] = True
