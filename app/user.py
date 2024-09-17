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
from werkzeug.exceptions import abort
import requests
import asyncio, aiohttp, json, os
import random  # for default location
import functools  # for database .fetchone() method
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from . import *
from .models import *

bp = Blueprint("user", __name__, url_prefix="/user")

FOURSQUARE_API_URL = "https://api.foursquare.com/v3/places/search"
FOURSQUARE_API_KEY = "fsq3XflsHeDs8cP703mPhp/K64ZuJYHFra2NGkn+SmjbPZM="
FOURSQUARE_API_PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"
FOURSQUARE_API_TIPS = "https://api.foursquare.com/v3/places/{fsq_id}/tips"
FOURSQUARE_API_DETAILS = "https://api.foursquare.com/v3/places/{fsq_id}"
OPENWEATHERMAP_API_KEY = "3495e8b531e0caf889157008e17fcca6"


async def get_places_data(city, categories):
    headers = {"accept": "application/json", "Authorization": FOURSQUARE_API_KEY}
    params = {}
    city = city + ", Ph"

    if city:
        params["near"] = city
    if categories:
        params["categories"] = categories

    params["sort"] = "POPULARITY"
    params["fields"] = "fsq_id,categories,geocodes,location,name"
    params["limit"] = 9

    async with aiohttp.ClientSession() as session:
        # First, get the weather data for the city
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        async with session.get(weather_url) as weather_response:
            if weather_response.status == 200:
                weather = await weather_response.json()
            else:
                # another location around the city
                own_params = {
                    "near": city + ", Ph",
                }
                async with session.get(
                    FOURSQUARE_API_URL,
                    headers=headers,
                    params=own_params,
                ) as response:
                    if response.status == 200:
                        get_place = await response.json()
                        get_place = (
                            get_place.get("context", {})
                            .get("geo_bounds", {})
                            .get("circle", {})
                            .get("center", {})
                        )

                        if get_place:
                            latitude = get_place.get("latitude")
                            longitude = get_place.get("longitude")
                            if latitude is not None and longitude is not None:
                                new_weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
                                async with session.get(
                                    new_weather_url
                                ) as weather_response:
                                    if weather_response.status == 200:
                                        weather = await weather_response.json()
                                    else:
                                        weather = None
                            else:
                                weather = None
                        else:
                            weather = None

        # Now, get the place data
        async with session.get(
            FOURSQUARE_API_URL, headers=headers, params=params
        ) as response:
            if response.status == 200:
                places = await response.json()
                places = places.get("results", [])

                places_details = []

                for place in places:
                    place_dict = dict(place)
                    fsq_id = place.get("fsq_id")

                    # Check if the place has been visited by the user
                    visited_row = db.session.execute(
                        select(Visited)
                        .where(Visited.fsq_id == fsq_id)
                        .where(Visited.user_id == g.user.id)
                    ).fetchone()
                    place_dict["visited"] = bool(visited_row)

                    # Check if the place has been liked by the user
                    liked_row = db.session.execute(
                        select(Liked)
                        .where(Liked.fsq_id == fsq_id)
                        .where(Liked.user_id == g.user.id)
                    ).fetchone()
                    place_dict["liked"] = bool(liked_row)

                    # URLs for API calls
                    photo_url = (
                        FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=4"
                    )
                    tips_url = FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=1"

                    # Concurrent async API calls for photos and tips
                    async with session.get(
                        photo_url, headers=headers
                    ) as photo_response, session.get(
                        tips_url, headers=headers
                    ) as tips_response:

                        # Process photos
                        if photo_response.status == 200:
                            photos = await photo_response.json()
                            place_dict["photos"] = photos if photos else []
                        else:
                            place_dict["photos"] = []

                        # Process tips
                        if tips_response.status == 200:
                            tips = await tips_response.json()
                            place_dict["tips"] = tips if tips else {}
                        else:
                            place_dict["tips"] = {}

                    # Add city weather to the place details
                    place_dict["weather"] = weather
                    places_details.append(place_dict)

                return places_details
            else:
                return None  # if API call fails


@bp.route("/", methods=("GET", "POST"))
def index():
    from app.auth import login_required

    @login_required
    async def inner():
        user_id = g.user.id
        # Query for visited places
        visited_query = (
            select(Visited)
            .where(Visited.user_id == user_id)
            .order_by(desc(Visited.created))
        )
        visited = db.session.execute(visited_query).scalars().all()
        # Query for liked places
        likes_query = select(Liked.fsq_id).where(Liked.user_id == user_id)
        likes = db.session.execute(likes_query).scalars().all()

        city = g.user.province
        categories = "12000,19000,16000,17000,10000,13000"
        places = await get_places_data(city, categories)
        myvisited = await get_visited_places_data(visited)

        unvisited_places = [place for place in places if not place["visited"]]
        unvisited_places = unvisited_places[:3]

        today = datetime.now().strftime("%b %d, %Y")

        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == user_id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        # limit to 2
        schedules = [schedule for schedule in schedules[:2]]

        schedules_list = []
        for row in schedules:
            schedule = row[0]  # Access the Plans object
            schedule_dict = {
                "id": schedule.id,
                "place_name": schedule.place_name,
                "user_id": schedule.user_id,
                "status": schedule.status,
                "notes": schedule.notes,
                "date": None,
            }

            # Format the date if it's available
            if schedule.date:
                try:
                    date_obj = datetime.strptime(str(schedule.date), "%Y-%m-%d")
                    schedule_dict["date"] = date_obj.strftime("%b %d, %Y")
                except ValueError:
                    schedule_dict["date"] = "Invalid Date"

            schedules_list.append(schedule_dict)

        if places:
            return render_template(
                "user/index.html",
                places=places,
                city=city,
                visited=visited,
                likes=likes,
                myvisited=myvisited,
                unvisited_places=unvisited_places,
                schedules=schedules_list,
                today=today,
                count_schedule=count_schedule,
            )
        else:
            return "Error: Failed to fetch places data."

    return asyncio.run(inner())


@bp.route("/popular", methods=("GET", "POST"))
def popular():
    from app.auth import login_required

    @login_required
    async def inner(city=None, categories=None):

        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        if request.method == "POST":
            city = request.form.get("city", "Philippines")
            categories = request.form.get("category")
            places = await get_places_data(city, categories)

            if places:
                return render_template(
                    "user/popular.html",
                    places=places,
                    city=city,
                    categories=categories,
                    count_schedule=count_schedule,
                )
            else:
                return "Error: Failed to fetch places data."
        else:

            city = g.user.province
            categories = categories or request.args.get(
                "categories", "12000,19000,16000,17000,10000,13000"
            )
            places = await get_places_data(city, categories)

            print(city)
            if places:
                return render_template(
                    "user/popular.html",
                    places=places,
                    city=city,
                    categories=categories,
                    count_schedule=count_schedule,
                )
            else:
                return "Error: Failed to fetch places data."

    return asyncio.run(inner())


@bp.route("/popular/<fsq_id>")
def place_info(fsq_id):
    from app.auth import login_required

    @login_required
    async def inner():

        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        place = await get_place_data(fsq_id)
        todaydate = datetime.now().strftime("%Y-%m-%d")

        get_plans = db.session.execute(
            select(Plans).where(Plans.user_id == g.user.id, Plans.fsq_id == fsq_id)
        ).fetchone()

        get_plans_dict = []

        if get_plans:
            # Use _mapping to convert row to a dictionary-like object
            plan = get_plans[0]
            get_plans_dict = {
                "id": plan.id,
                "place_name": plan.place_name,
                "user_id": plan.user_id,
                "status": plan.status,
                "notes": plan.notes,
                "date": plan.date,
            }

            # Check and format the date if it exists
            if plan.date:
                try:
                    date_obj = datetime.strptime(plan.date, "%Y-%m-%d")
                    get_plans_dict["formatted_date"] = date_obj.strftime("%B %d, %Y")
                except ValueError:
                    get_plans_dict["formatted_date"] = "Invalid Date"

        else:
            get_plans_dict = None

        if place:
            return render_template(
                "user/place_info.html",
                place=place,
                todaydate=todaydate,
                plans=get_plans_dict,
                count_schedule=count_schedule,
            )
        else:
            return "Error: Failed to fetch place data."

        return render_template("user/place_info.html")

    return asyncio.run(inner())


async def get_place_data(fsq_id):
    headers = {"accept": "application/json", "Authorization": FOURSQUARE_API_KEY}
    params = {"fields": "fsq_id,categories,geocodes,location,name,related_places"}

    # Initialize a dictionary to store the details of the place
    place_details = {}

    async with aiohttp.ClientSession() as session:
        # Fetch basic details of the place
        async with session.get(
            FOURSQUARE_API_DETAILS.format(fsq_id=fsq_id), params=params, headers=headers
        ) as details_response:
            if details_response.status == 200:
                details = await details_response.json()

                # Add basic details to the dictionary
                place_details = details

                # Check if the place has been visited by the user
                visited_row = db.session.execute(
                    select(Visited)
                    .where(Visited.fsq_id == fsq_id)
                    .where(Visited.user_id == g.user.id)
                ).fetchone()
                place_details["visited"] = bool(visited_row)

                # Check if the place has been liked by the user
                liked_row = db.session.execute(
                    select(Liked)
                    .where(Liked.fsq_id == fsq_id)
                    .where(Liked.user_id == g.user.id)
                ).fetchone()
                place_details["liked"] = bool(liked_row)

                lat = details.get("geocodes", {}).get("main", {}).get("latitude")
                lon = details.get("geocodes", {}).get("main", {}).get("longitude")

                if lat and lon:
                    # Fetch photos
                    async with session.get(
                        FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=5",
                        headers=headers,
                    ) as photo_response:
                        if photo_response.status == 200:
                            photos = await photo_response.json()
                            place_details["photos"] = photos if photos else []
                        else:
                            place_details["photos"] = []

                    # Fetch weather
                    async with session.get(
                        f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
                    ) as weather_response:
                        if weather_response.status == 200:
                            weather = await weather_response.json()
                            place_details["weather"] = weather
                        else:
                            place_details["weather"] = {}

                    tip_params = {
                        "fields": "text,agree_count,disagree_count,created_at"
                    }
                    async with session.get(
                        FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=5",
                        headers=headers,
                        params=tip_params,
                    ) as tips_response:
                        if tips_response.status == 200:
                            tips = await tips_response.json()

                            formatted_tips = []
                            for tip in tips:
                                created_at = tip.get("created_at")
                                if created_at:
                                    # Parse ISO date string
                                    created_at_obj = datetime.strptime(
                                        created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                                    )
                                    # Format the date (e.g., "June 14, 2018")
                                    tip["created_at"] = created_at_obj.strftime(
                                        "%B %d, %Y"
                                    )

                                formatted_tips.append(tip)

                            place_details["tips"] = (
                                formatted_tips if formatted_tips else []
                            )
                            place_details["tips_count"] = len(formatted_tips)
                        else:
                            place_details["tips"] = []
                else:
                    place_details["photos"] = []
                    place_details["weather"] = {}
                    place_details["tips"] = {}

                related_places = details.get("related_places", {}).get("children", [])

                items = 0
                for related_place in related_places:
                    # Fetch photos for each related place
                    async with session.get(
                        FOURSQUARE_API_PHOTOS_URL.format(fsq_id=related_place["fsq_id"])
                        + "?limit=4",
                        headers=headers,
                    ) as photo_response:
                        # check if there is a photo
                        if photo_response.status == 200:
                            photos = await photo_response.json()
                            if photos:
                                related_place["photos"] = photos
                                items = items + 1

                    if items == 12:
                        break

                # Return the place details including related places
                place_details["related_places_photos"] = related_places

            else:
                return None

    # Return the complete place details with photos, weather, and tips
    return place_details


@bp.route("/add_visited", methods=("GET", "POST"))
def add_to_visited():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            fsq_id = request.form.get("place_id")
            error = None

            if not fsq_id:
                error = "Error while adding the place. Please try again."

            if error is None:
                try:
                    visited = Visited(fsq_id=fsq_id, user_id=g.user.id)
                    db.session.add(visited)
                    db.session.commit()

                except IntegrityError:
                    db.session.rollback()
                    error = f"The place is already in your visited list."
                else:
                    return redirect(url_for("user.place_info", fsq_id=fsq_id))
            flash(error, "danger")
        return redirect(url_for("user.place_info", fsq_id=fsq_id))

    return asyncio.run(inner())


@bp.route("/remove_visited", methods=["POST"])
def remove_to_visited():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            fsq_id = request.form.get("place_id")
            error = None

            if not fsq_id:
                error = "Error while unliking the place. Please try again."
            if error is None:
                try:
                    visited = (
                        db.session.query(Visited)
                        .filter_by(fsq_id=fsq_id, user_id=g.user.id)
                        .first()
                    )
                    if visited:
                        db.session.delete(visited)
                        db.session.commit()
                    else:
                        error = "You don't have this place in your visited list."

                except IntegrityError:
                    db.session.rollback()
                    error = "The place is already in your unvisited list."
                else:
                    return redirect(request.referrer)
            flash(error, "danger")

            return redirect(request.referrer)

    return asyncio.run(inner())


@bp.route("/add_liked", methods=("GET", "POST"))
def add_to_liked():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            fsq_id = request.form.get("place_id")
            error = None
            if not fsq_id:
                error = "Error while liking the place. Please try again."
            if error is None:
                try:
                    liked = Liked(fsq_id=fsq_id, user_id=g.user.id)
                    db.session.add(liked)
                    db.session.commit()

                except IntegrityError:
                    db.session.rollback()
                    error = "The place is already in your liked list."
                else:
                    return redirect(request.referrer)

            flash(error, "danger")

            return redirect(request.referrer)

    return asyncio.run(inner())


@bp.route("/remove_liked", methods=("GET", "POST"))
def remove_to_liked():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            fsq_id = request.form.get("place_id")
            error = None

            if not fsq_id:
                error = "Error while unliking the place. Please try again."
            if error is None:
                try:
                    liked = (
                        db.session.query(Liked)
                        .filter_by(fsq_id=fsq_id, user_id=g.user.id)
                        .first()
                    )
                    if liked:
                        db.session.delete(liked)
                        db.session.commit()
                    else:
                        error = "You don't have this place in your liked list."

                except IntegrityError:

                    error = "The place is already in your unliked list."
                else:
                    return redirect(request.referrer)
            flash(error, "danger")

            return redirect(request.referrer)

    return asyncio.run(inner())


async def get_visited_places_data(fsq_id):
    headers = {"accept": "application/json", "Authorization": FOURSQUARE_API_KEY}
    params = {"fields": "fsq_id,categories,geocodes,location,name"}

    places_details = []  # store the details of each place

    async with aiohttp.ClientSession() as session:
        tasks = []
        place_dict = []

        for place in fsq_id:
            # Convert place to a dictionary
            place_dict = {
                "fsq_id": place.fsq_id,
            }
            fsq_id = place_dict["fsq_id"]

            details_url = FOURSQUARE_API_DETAILS.format(fsq_id=fsq_id)
            tasks.append(
                fetch_place_details(
                    session, details_url, params, headers, place_dict, db
                )
            )

        places_details = await asyncio.gather(*tasks)

    return places_details


async def fetch_place_details(session, details_url, params, headers, place_dict, db):
    async with session.get(
        details_url, params=params, headers=headers
    ) as details_response:
        if details_response.status == 200:
            details = await details_response.json()
            place_dict.update(details)  # Update the place_dict with details fetched

            fsq_id = place_dict["fsq_id"]

            # Check if the place has been visited by the user
            visited_row = db.session.execute(
                select(Visited)
                .where(Visited.fsq_id == fsq_id)
                .where(Visited.user_id == g.user.id)
            ).fetchone()
            place_dict["visited"] = bool(visited_row)

            # Check if the place has been liked by the user
            liked_row = db.session.execute(
                select(Liked)
                .where(Liked.fsq_id == fsq_id)
                .where(Liked.user_id == g.user.id)
            ).fetchone()
            place_dict["liked"] = bool(liked_row)

            lat = place_dict.get("geocodes", {}).get("main", {}).get("latitude")
            lon = place_dict.get("geocodes", {}).get("main", {}).get("longitude")

            if lat and lon:
                photo_url = FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=4"
                weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
                tips_url = FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=1"

                # Fetch photos
                photo_task = session.get(photo_url, headers=headers)
                weather_task = session.get(weather_url)
                tips_task = session.get(tips_url, headers=headers)

                photos_response, weather_response, tips_response = await asyncio.gather(
                    photo_task, weather_task, tips_task
                )

                if photos_response.status == 200:
                    photos = await photos_response.json()
                    place_dict["photos"] = photos if photos else []
                else:
                    place_dict["photos"] = []

                if weather_response.status == 200:
                    weather = await weather_response.json()
                    place_dict["weather"] = weather
                else:
                    place_dict["weather"] = {}

                if tips_response.status == 200:
                    tips = await tips_response.json()
                    place_dict["tips"] = tips
                else:
                    place_dict["tips"] = {}

            return place_dict
        else:
            return None


@bp.route("/visited", methods=("GET", "POST"))
def visited():
    from app.auth import login_required

    @login_required
    async def inner():
        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        items_per_page = 6
        page = request.args.get("page", 1, type=int)
        offset = (page - 1) * items_per_page

        visited = (
            Visited.query.filter_by(user_id=g.user.id)
            .order_by(Visited.created.desc())
            .offset(offset)
            .limit(items_per_page)
            .all()
        )

        total_visited = Visited.query.filter_by(user_id=g.user.id).count()

        total_pages = (total_visited + items_per_page - 1) // items_per_page
        places = await get_visited_places_data(visited)

        # Calculate items start and end for the current page
        items_start = offset + 1
        items_end = min(offset + items_per_page, total_visited)

        return render_template(
            "user/visited.html",
            places=places,
            page=page,
            total_pages=total_pages,
            total_entries=total_visited,
            items_start=items_start,
            items_end=items_end,
            items_per_page=items_per_page,
            count_schedule=count_schedule,
        )

    return asyncio.run(inner())


@bp.route("/likes", methods=("GET", "POST"))
def liked():
    from app.auth import login_required

    @login_required
    async def inner():
        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        items_per_page = 6
        page = request.args.get("page", 1, type=int)
        offset = (page - 1) * items_per_page

        liked = (
            Liked.query.filter_by(user_id=g.user.id)
            .order_by(Liked.created.desc())
            .offset(offset)
            .limit(items_per_page)
            .all()
        )

        total_likes = Liked.query.filter_by(user_id=g.user.id).count()

        total_pages = (total_likes + items_per_page - 1) // items_per_page
        places = await get_visited_places_data(liked)

        # Calculate items start and end for the current page
        items_start = offset + 1
        items_end = min(offset + items_per_page, total_likes)

        return render_template(
            "user/liked.html",
            places=places,
            page=page,
            total_pages=total_pages,
            total_entries=total_likes,
            items_start=items_start,
            items_end=items_end,
            items_per_page=items_per_page,
            count_schedule=count_schedule,
        )

    return asyncio.run(inner())
