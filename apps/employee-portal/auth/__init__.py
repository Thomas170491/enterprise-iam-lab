from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask import session,current_app
from auth.user import User 

oauth = OAuth()
login_manager = LoginManager()

login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    user_data = session.get("user")

    if not user_data:
        return None

    if user_data.get("sub") != user_id:
        current_app.logger.warning(
            "Flask-Login user ID mismatch"
        )
        session.clear()
        return None

    return User(
        sub=user_data["sub"],
        username=user_data["username"],
        name=user_data["name"],
        email=user_data["email"],
        realm_roles=user_data.get("realm_roles", []),
        client_roles=user_data.get("client_roles", [])
    )