from functools import wraps
from flask import abort 
from flask_login import current_user  



def client_role_required(required_role):
    """
    Require the authenticated user to possess a specific
    iam-admin-portal client role.

    Authentication itself remains the responsibility
    of Flask-Login's @login_required decorator.
    """

    def decorator(view_function) :
        @wraps(view_function)
        def wrapped_view(*args,**kwargs):
            if required_role not in current_user.client_roles :
                abort(403)

            return view_function (*args,**kwargs)
        return wrapped_view
    return decorator


        
