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
from app.db import get_db, close_db
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
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        error = None
        user = db.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

        if user is None:
            error = "Email or Password is incorrect."
        elif not check_password_hash(user["password"], password):
            error = "Email or Password is incorrect."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("user.index"))

        flash(error, "danger")

    return render_template("auth/login.html")


@bp.route("/reset", methods=("POST", "GET"))
def reset_password_request():
    if request.method == "POST":
        email = request.form.get("email")
        db = get_db()
        error = None
        if not email:
            error = "Email is required."

        if error is None:
            user = db.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()
            if user is None:
                error = "Email is not registered."
            else:
                token = s.dumps(email, salt="reset-password")
                msg = Message(
                    "Reset Password - City Explorer",
                    recipients=[email],
                )
                link = url_for(
                    "auth.reset_password", token=token, _id=user["id"], _external=True
                )
                msg.body = f"Hi {user['firstname']}\nPlease click the link to reset your password: {link}"
                try:
                    mail.send(msg)
                    flash(
                        "A password reset link has been sent to your email address!",
                        "success",
                    )
                except Exception as e:
                    flash(f"Failed to send email. Error: {e}", "danger")

                return redirect(url_for("auth.reset_password_request"))
            flash(error, "danger")
    return render_template("auth/reset_password_request.html")


class PasswordForm(Form):
    password = PasswordField(
        "New Password",
        [
            validators.DataRequired(),
            validators.EqualTo("confirm_password", message="Password must match"),
        ],
    )
    confirm_password = PasswordField("Repeat Password")


@bp.route("/reset/<token>/<_id>", methods=("GET", "POST"))
def reset_password(token, _id):
    db = get_db()
    user = db.execute("SELECT * FROM user WHERE id = ?", (_id,)).fetchone()
    try:
        # Decode the token to get the email
        email = s.loads(token, salt="reset-password", max_age=3600)
    except Exception:
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.reset_password_request"))

    # Retrieve the user by ID and verify the email matches

    if user is None or user["email"] != email:
        flash("Invalid reset request.", "danger")
        return redirect(url_for("auth.reset_password_request"))

    return render_template("auth/reset_password.html", user=user)


@bp.route("/save/password/<id>", methods=("GET", "POST"))
def save_password(id):

    form = PasswordForm(request.form)
    db = get_db()
    if request.method == "POST" and form.validate():
        new_password = request.form.get("password")
        if not new_password:
            flash("Password is required.", "danger")
        else:
            db.execute(
                "UPDATE user SET password = ? WHERE id = ?",
                (generate_password_hash(new_password), id),
            )
            db.commit()
            close_db(db)
            flash("Your password has been reset successfully!", "success")
            return redirect(url_for("auth.login"))

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")

    return render_template("auth/reset_password.html", form=form)


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
    async def wrapped_view(*args, **kwargs):
        if g.user is None or g.user["verified"] == "false":
            flash("Please verify your email before accessing this page.", "warning")
            return redirect(url_for("auth.login"))

        return await view(*args, **kwargs)

    return wrapped_view
