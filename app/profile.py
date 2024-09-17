from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from wtforms import Form, StringField, PasswordField, validators, ValidationError
from wtforms.validators import DataRequired
from sqlalchemy.exc import IntegrityError
from .models import *
import json
import os
import asyncio
from sqlalchemy import select, desc
import aiohttp


bp = Blueprint("profile", __name__, url_prefix="/profile")


class ValidateForm(Form):
    firstname = StringField("firstname", [validators.Length(min=3, max=35)])
    lastname = StringField("lastname", [validators.Length(min=3, max=35)])
    province = StringField("province", [validators.Length(min=4)])
    email = StringField("email", [validators.Length(min=6, max=35)])


@bp.route("/", methods=("GET", "POST"))
def index():
    from app.auth import login_required

    @login_required
    async def inner():
        form = ValidateForm(request.form)
        if request.method == "POST" and form.validate():
            user = User.query.get_or_404(g.user.id)
            if user:
                user.firstname = form.firstname.data
                user.lastname = form.lastname.data
                user.province = form.province.data
                user.email = form.email.data
                db.session.commit()
                flash("Profile updated successfully!", "success")
                return redirect(url_for("profile.index"))

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

        provinces_list = sorted(list(provinces))
        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        return render_template(
            "user/profile.html",
            data=provinces_list,
            form=form,
            count_schedule=count_schedule,
        )

    return asyncio.run(inner())


@bp.route("/update/character", methods=("GET", "POST"))
def update_character():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            character = request.form.get("character")
            try:
                user = User.query.get_or_404(g.user.id)
                if user:
                    user.character = character
                    db.session.commit()
                    flash("Character updated successfully!", "success")
                    return redirect(url_for("profile.index"))
                else:
                    flash("User not found.", "danger")

            except IntegrityError:
                db.session.rollback()
                flash("An error occurred while updating the character.", "danger")
            except Exception as e:
                flash(f"An error occurred: {str(e)}", "danger")

        return redirect(url_for("profile.index"))

    return asyncio.run(inner())
