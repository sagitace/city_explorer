import os

from flask import Flask, render_template, redirect, url_for, g
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

mail = Mail()
s = URLSafeTimedSerializer("iojksdwyhdnmdsokmd,d/sd/wjwk")


def create_app():
    # create and configure appp
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "app.sqlite"),
    )

    # mail configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 465
    app.config["MAIL_USERNAME"] = "labiniace.barlas35@gmail.com"
    app.config["MAIL_PASSWORD"] = "xwaqmewcfybtwsst"
    app.config["MAIL_USE_TLS"] = False
    app.config["MAIL_USE_SSL"] = True
    app.config["MAIL_DEFAULT_SENDER"] = "labiniace.barlas35@gmail.com"
    mail.init_app(app)

    app.config.from_pyfile("config.py", silent=True)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    def index():
        if g.user is not None:
            return redirect(url_for("user.index"))
        return render_template(
            "index.html",
        )

    from . import db

    db.init_app(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import user

    app.register_blueprint(user.bp)
    app.add_url_rule("/", endpoint="index")

    return app
