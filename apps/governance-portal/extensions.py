from flask_smorest import Api


# Flask-Smorest API extension.
#
# We create it here without binding it immediately
# to a Flask application. app.py will initialize it
# inside the application factory.
api = Api()
