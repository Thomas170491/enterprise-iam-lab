from functools import wraps
from flask import jsonify
from flask_login import current_user

def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs) :
        if not current_user.is_authenticated :
            return jsonify(
               { 
                "error" : "authentification_required",
                "message" : "Authentification is required"
                }
            ),401
        return view(*args,**kwargs)
    return wrapped

