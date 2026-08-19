from authlib.integrations.flask_client import OAuth
from flask import session, current_app
from auth.user import User 
from extensions import login_manager 

@login_manager.user_loader
def load_user(user_id):
    user_data = session.get("user")

    if not user_data :
        return None

    if user_data.get("sub") != user_id :
        current_app.logger.warning(
            "Flask Login user ID mismatch"
        )
        session.clear()
        return None

    return User(
        sub = user_data["sub"],
        username= user_data["username"],
        email= user_data["email"],
        client_roles= user_data.get("client_roles", []),
        realm_roles= user_data.get("realm_roles",[])

    )

