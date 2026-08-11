


from flask import Flask 
from config import Config
from flask_session import Session
from portal.routes import bp_portal 
from auth.__init__ import oauth


sess = Session()


def create_app():

    #Initialize app
    app = Flask(__name__)

    #Grab configuration from config.py here
    app.config.from_object(Config)

    #Initialize sessionsand OAuth
    sess.init_app(app)
    oauth.init_app(app)

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

    return app

app=create_app()

 