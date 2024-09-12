import os

from flask import Flask, render_template, redirect, url_for, g
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import asyncio, aiohttp

mail = Mail()
s = URLSafeTimedSerializer("iojksdwyhdnmdsokmd,d/sd/wjwk")

FOURSQUARE_API_KEY = "fsq3XflsHeDs8cP703mPhp/K64ZuJYHFra2NGkn+SmjbPZM="
FOURSQUARE_API_PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"
FOURSQUARE_API_URL = "https://api.foursquare.com/v3/places/search"


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

    from . import db

    db.init_app(app)

    from . import auth

    app.register_blueprint(auth.bp)

    from . import user

    app.register_blueprint(user.bp)
    app.add_url_rule("/", endpoint="index")

    return app
