from functools import wraps

from flask import abort
from flask_login import current_user

def realm_role_required(required_role):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            if required_role not in current_user.realm_roles :
                 abort(403)
            return view_function(*args,**kwargs)
        return wrapped_view
    return decorator

def client_role_required(required_role):
    def decorator(view_function):
        @wraps(view_function) 
        def wrapped_view(*args,**kwargs):
            if required_role not in current_user.client_roles:
                return abort(403)
            return view_function(*args,**kwargs)
        return wrapped_view
    return decorator

