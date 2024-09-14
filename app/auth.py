import functools
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import get_db
from app.user import index
from . import *
from flask_mail import Message
from wtforms import Form, StringField, PasswordField, validators
import json, os

bp = Blueprint("auth", __name__, url_prefix="/auth")


class RegistrationForm(Form):
    firstname = StringField("firstname", [validators.Length(min=4, max=35)])
    lastname = StringField("lastname", [validators.Length(min=4, max=35)])
    province = StringField("province", [validators.length(min=4)])
    email = StringField("email", [validators.Length(min=6, max=35)])
    password = PasswordField(
        "Password",
        validators=[
            validators.DataRequired(),
            validators.Length(
                min=8, message="Password must be at least 8 characters long"
            ),
        ],
    )


@bp.route("/register", methods=("POST", "GET"))
def register():
    if g.user is None:
        form = RegistrationForm(request.form)
        if request.method == "POST" and form.validate():
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO user (firstname, lastname, province, email, password) VALUES (?, ?, ?, ?, ?)",
                    (
                        form.firstname.data,
                        form.lastname.data,
                        form.province.data,
                        form.email.data,
                        generate_password_hash(form.password.data),
                    ),
                )
                db.commit()

                token = s.dumps(form.email.data, salt="email-confirm")

                msg = Message(
                    "Email Verification - City Explorer",
                    recipients=[form.email.data],
                )
                link = url_for("auth.confirm", token=token, _external=True)
                msg.body = f"Hi {form.firstname.data}\nPlease click the link to verify your email: {link}"

                # Send the email
                try:
                    mail.send(msg)
                    flash(
                        "A verification email has been sent to your email address!",
                        "info",
                    )
                except Exception as e:
                    flash(f"Failed to send email. Error: {e}", "danger")
                    return redirect(url_for("auth.register"))

            except db.IntegrityError:
                error = f"{form.email.data} is already registered."
            else:
                return redirect(url_for("auth.login"))
            flash(error, "danger")
        try:
            json_file_path = os.path.join(
                current_app.static_folder,
                "philippine_provinces_cities_municipalities_and_barangays_2019v2.json",
            )
            with open(json_file_path) as myjsonfile:
                mydata = json.load(myjsonfile)
        except FileNotFoundError:
            flash("Data file not found.", "danger")
            mydata = []
        provinces = set()
        for region_key, region_value in mydata.items():
            if "province_list" in region_value:
                for province_key in region_value["province_list"].keys():
                    provinces.add(province_key)

        # Convert the set to a sorted list
        provinces_list = sorted(list(provinces))

        return render_template("auth/register.html", data=provinces_list)
    else:
        return redirect(url_for("user.index"))


@bp.route("/confirm/<token>")
def confirm(token):
    try:
        # validate
        email = s.loads(
            token, salt="email-confirm", max_age=3600
        )  # Token is valid for 1hr
    except SignatureExpired:
        return "<h1>The token is expired!</h1>"

    user = get_db().execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

    if user:
        get_db().execute('UPDATE user SET verified = "true" WHERE email = ?', (email,))
        get_db().commit()
    else:
        return "<h1>Invalid token</h1>"

    flash("Your email has been verified successfully!", "success")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is None:
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]
            db = get_db()
            error = None
            user = db.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

            if user is None:
                error = "Email don't exist."
            elif not check_password_hash(user["password"], password):
                error = "Incorrect password."

            if error is None:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("user.index"))

            flash(error, "danger")

        return render_template("auth/login.html")
    else:
        return redirect(url_for("user.index"))


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        if (
            g.user["verified"] == "false"
        ):  # ensures that the user has verified their email
            flash("Please verify your email before accessing this page.", "warning")
            return redirect(url_for("auth.register"))

        return view(**kwargs)

    return wrapped_view
