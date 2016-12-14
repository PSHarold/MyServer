import flask
import random, string
from config import Config
from flask_moment import Moment
from flask_mail import Mail, Message
config = Config()

from flask_bootstrap import Bootstrap


import general


bootstrap = Bootstrap()
moment = Moment()
mail = Mail()



def create_app():
    app = flask.Flask(__name__)
    config.init_app(app)
    bootstrap = Bootstrap()
    bootstrap.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
