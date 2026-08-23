def test_health_endpoint(client) :
    """
    The REST health endpoint should return the 
    expected JSON structure.
    """
    response = client.get(
        "api/v1/health"
    )

    assert response.status_code == 200
    assert response.get_json()=={
        "status" : "ok",
        "application" : "NovaSecure IAM Governance Portal"    
    }

def test_openapi_document(client):
    """
    Flask-Smorest should expose the generated
    OpenAPI specification.
    """

    response = client.get("/api/openapi.json")

    assert response.status_code == 200

    document = response.get_json()

    assert document["openapi"] == "3.0.3"

    assert document["info"]["title"] == "NovaSecure IAM Governance API"

    assert "/api/v1/health" in document["paths"]

def test_expected_routes_are_registered(app):
    """
    Verify the fundamental application routes
    actually exist in Flask.
    """

    routes = {
        rule.rule 
        for rule in app.url_map.iter_rules()
    }

    assert "/" in routes
    assert "/login" in routes
    assert "/auth/callback" in routes
    assert "/api/v1/health" in routes
    assert "/api/openapi.json" in routes