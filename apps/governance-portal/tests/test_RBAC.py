def _login_test_user(client,client_roles):
        """
    Place a test identity directly into the Flask
    session.

    This tests RBAC independently from the OIDC flow,
    which already has its own test suite.
    """
        with client.session_transaction() as sess:
            print(dict(sess))
            sess["user"] = {
                "sub": "test-subject",
                "username": "test-user",
                "name": "Test User",
                "email": "test@example.test",
                "client_roles": client_roles,
                "realm_roles": [],
                }
            
            # Flask-Login stores the authenticated user's
            # ID separately.
            sess["_user_id"] = "test-subject"

            # Mirrors login_user().
            sess["_fresh"] = True



def test_dashboard_allows_authorized_user(client):
      _login_test_user(
            client, 
            [
               "iam-dashboard-access",
               "identity-viewer"
            ])

      response = client.get("/")
      print(response)
      assert response.status_code == 200

def test_dashboard_denies_unauthorized_user(client):
    _login_test_user(
            client, 
            [
               "identity-viewer"
            ])
    
    response = client.get("/")
    print(response)
    assert response.status_code == 403

def test_dashboard_requires_authentification(client):
      response =client.get("/", follow_redirects = False)
      print(response)
      assert response.status_code ==302
      assert "/login" in response.headers["Location"]
      

      
