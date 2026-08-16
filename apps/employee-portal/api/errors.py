from flask import jsonify


def api_error(error, message, status_code):
    return jsonify({
        "error": error,
        "message": message,
    }), status_code