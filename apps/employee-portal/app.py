from flask import Flask 

from config import Config 
from flask_session import Session
from portal.routes import bp_portal 

sess = Session()

def create_app():
    #Initialize app
    app = Flask(__name__)

    #Grab configuration from config.py here
    app.config.from_object(Config)

    #Initialize sessions
    sess.init_app(app)

    #Register blueprints
    app.register_blueprint(bp_portal)

    return app

app=create_app()

 