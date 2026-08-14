from flask import Flask,render_template
from config import Config
from flask_session import Session
from portal.routes import bp_portal 
from auth import oauth,login_manager
from auth.routes import bp_auth
from flask_wtf.csrf import CSRFProtect


sess = Session()
csrf = CSRFProtect()


def create_app():

    #Initialize app
    app = Flask(__name__)

    #Grab configuration from config.py here
    app.config.from_object(Config)

    #Initialisations

    sess.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    #OAuth registration
    oauth.register(
        name="keycloak",
        client_id  = app.config["KEYCLOAK_CLIENT_ID"],
        client_secret  = app.config["KEYCLOAK_CLIENT_SECRET"],
        server_metadata_url =  app.config["KEYCLOAK_METADATA_URL"],
        client_kwargs={
            "scope" : "openid profile email"
        }
    )



    #Register blueprints
    app.register_blueprint(bp_portal)
    app.register_blueprint(bp_auth)

    return app

app=create_app()

@app.errorhandler(403)
def forbidden(error):
    return render_template("access-denied.html"), 403