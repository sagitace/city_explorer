import os
from flask import Flask, render_template, redirect, url_for, g
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import asyncio
import aiohttp
from flask_migrate import Migrate
from .models import db

mail = Mail()

FOURSQUARE_API_KEY = "fsq3XflsHeDs8cP703mPhp/K64ZuJYHFra2NGkn+SmjbPZM="
FOURSQUARE_API_PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"
FOURSQUARE_API_URL = "https://api.foursquare.com/v3/places/search"


def create_app():
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # SQLAlchemy configuration
    #app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    #postgres
    #postgresql://explorer_a53g_user:Fkt354KFUlUNTx4D1sxXCCGfmIwlLDnV@dpg-crppttrv2p9s7389tcc0-a.oregon-postgres.render.com/explorer_a53g
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    app.config["SECRET_KEY"] = "shudjnawgyhbjnkdmawk923"

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Mail configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 465
    app.config["MAIL_USERNAME"] = "labiniace.barlas35@gmail.com"
    app.config["MAIL_PASSWORD"] = "xwaqmewcfybtwsst"
    app.config["MAIL_USE_TLS"] = False
    app.config["MAIL_USE_SSL"] = True
    app.config["MAIL_DEFAULT_SENDER"] = "labiniace.barlas35@gmail.com"

    mail.init_app(app)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    async def get_photos_data(locations):
        headers = {"accept": "application/json", "Authorization": FOURSQUARE_API_KEY}

        places_with_photos = []
        params = {
            "fields": "fsq_id,location",
            "near": locations,
            "sort": "POPULARITY",
            "limit": 1,
            "categories": "16000",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                FOURSQUARE_API_URL, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    places = data.get("results", [])
                    for place in places:
                        place["details"] = place.get("location", [])
                        fsq_id = place.get("fsq_id")
                        photo_params = {
                            "classification": "outdoor",
                        }
                        photo_url = (
                            FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=1"
                        )

                        async with session.get(
                            photo_url, headers=headers, params=photo_params
                        ) as photo_response:
                            if photo_response.status == 200:
                                photos = await photo_response.json()
                                place["photos"] = photos if photos else []
                            else:
                                place["photos"] = []

                        places_with_photos.append(place)
        return places_with_photos

    @app.route("/")
    async def index():
        if g.user is not None:
            return redirect(url_for("user.index"))

        luzon = [
            "ifugao, ph",
        ]
        visayas = [
            "Bohol, Ph",
        ]
        mindanao = ["Siargao, Ph"]

        photos_luzon = await get_photos_data(luzon)
        photos_visayas = await get_photos_data(visayas)
        photos_mindanao = await get_photos_data(mindanao)

        return render_template(
            "index.html",
            photos_luzon=photos_luzon,
            photos_visayas=photos_visayas,
            photos_mindanao=photos_mindanao,
        )

    from . import auth
    from . import user
    from . import profile
    from . import schedule

    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(schedule.bp)

    app.add_url_rule("/", endpoint="index")

    return app
