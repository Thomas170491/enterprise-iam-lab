from flask import jsonify,request


def api_error(error, message, status_code):
    return jsonify({
        "error": error,
        "message": message,
    }), status_code

def register_api_error_handlers(app):

    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith("/api/"):
            return api_error(
                "authentication_required",
                "Authentication is required.",
                401,
            )

        return error

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api/"):
            return api_error(
                "forbidden",
                "Access to this resource is forbidden.",
                403,
            )

        return error

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api"):
            return api_error(
                "not_found",
                "API resource not found",
                404,
            )

        return error

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api/"):
            return api_error(
                "method_not_allowed",
                "HTTP method is not allowed for this endpoint.",
                405,
            )

        return error