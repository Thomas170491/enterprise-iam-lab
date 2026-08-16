from functools import wraps
from flask_login import current_user
from api.errors import api_error


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs) :
        if not current_user.is_authenticated :
            return api_error(
                "authentification_required",
                "Authentification is required",
                401,
            )
        return view(*args,**kwargs)
    return wrapped





