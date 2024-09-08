from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from app.db import get_db
import requests
import functools #for database .fetchone() method

bp = Blueprint('user', __name__, url_prefix='/user')

FOURSQUARE_API_URL = "https://api.foursquare.com/v3/places/search"
FOURSQUARE_API_KEY = "fsq3XflsHeDs8cP703mPhp/K64ZuJYHFra2NGkn+SmjbPZM="
FOURSQUARE_API_PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"
FOURSQUARE_API_TIPS = "https://api.foursquare.com/v3/places/{fsq_id}/tips"
FOURSQUARE_API_DETAILS = "https://api.foursquare.com/v3/places/{fsq_id}"
OPENWEATHERMAP_API_KEY = "3495e8b531e0caf889157008e17fcca6"

def get_places_data(city, categories):
    headers = {
        "accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {}
    city = city + ', Ph'
    
    if city:
        params["near"] = city
    if categories:
        params["categories"] = categories
    
    params["sort"] = 'POPULARITY' 
    params["fields"] = 'fsq_id,categories,geocodes,location,name'
           
    if city or categories:
        params["limit"] = 6
        response = requests.get(FOURSQUARE_API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            
            db = get_db() #connect to database
            
            places = response.json().get('results', [])
            for place in places:
                
                fsq_id = place.get('fsq_id')
                lon = place.get('geocodes', {}).get('main', {}).get('longitude')
                lat = place.get('geocodes', {}).get('main', {}).get('latitude')
                
                visited_row = db.execute("SELECT 1 FROM visited WHERE fsq_id = ? AND user_id = ?", (fsq_id, g.user['id'])).fetchone()
                
                if visited_row:
                    place['visited'] = True
                else:
                    place['visited'] = False
                
                photo_response = requests.get(FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=4", headers=headers)
                weather_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
                tips_response = requests.get(FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=1", headers=headers)
                
                if photo_response.status_code == 200:
                    photos = photo_response.json()  # return a list
                    place['photos'] = photos if photos else []  # Add the list of photos if it exists
                else:
                    place['photos'] = []
                    
                if weather_response.status_code == 200:
                    weather = weather_response.json()
                    place['weather'] = weather
                else:
                    place['weather'] = {}
                if tips_response.status_code == 200:
                    tips = tips_response.json()
                    place['tips'] = tips
                else:
                    place['tips'] = {}
                
            return places  # Return JSON data from the API
        else:
            return None  # Handle error if API call fails

def get_photos_data(locations):
    headers = {
        "accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }

    places_with_photos = []
    for location in locations:
        params = {
            "fields": 'fsq_id',
            "near": location,
            "sort": 'POPULARITY',
            "limit": 1,
            "categories": '19000,16000'
        }
        
        
        response = requests.get(FOURSQUARE_API_URL, headers=headers, params=params)
        if response.status_code == 200:
            places = response.json().get('results', [])
            for place in places:
                fsq_id = place.get('fsq_id')
                
                # Get Photos
                photo_response = requests.get(FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=1", headers=headers)
                if photo_response.status_code == 200:
                    photos = photo_response.json()  # return a list
                    place['photos'] = photos if photos else []  # Add the list of photos if it exists
                else:
                    place['photos'] = []
                    
                # lat = place.get('geocodes', {}).get('main', {}).get('latitude')
                # lon = place.get('geocodes', {}).get('main', {}).get('longitude')
                # weather_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
                # if weather_response.status_code == 200:
                #     place['weather'] = weather_response.json()
                # else:
                #     place['weather'] = {}

                places_with_photos.append(place)
        else:
            continue  # If API call fails, skip this location
    return places_with_photos    

@bp.route('/', methods=('GET', 'POST'))
def index():
    from app.auth import login_required
    @login_required
    def inner():
        
        # luzon = ['baguio, Ph', 'batangas, Ph', 'tagaytay, ph', 'makati, ph', 'ifugao, ph']
        # visayas = ['Boracay, Ph', 'Cebu, Ph', 'Bohol, Ph', 'Iloilo, Ph', 'Dumaguete, Ph']
        # mindanao = ['Davao, Ph', 'Camiguin, Ph', 'Siargao, Ph', 'Zamboanga, Ph']

        # photos_luzon = get_photos_data(luzon)
        # photos_visayas = get_photos_data(visayas)
        # photos_mindanao = get_photos_data(mindanao)
            
        # return render_template('user/index.html', photos_luzon=photos_luzon, photos_visayas=photos_visayas, photos_mindanao=photos_mindanao)
        return render_template('user/index.html')
    return inner()

@bp.route('/popular', methods=('GET', 'POST'))
def popular():
    from app.auth import login_required
    @login_required
    def inner():
        if request.method == 'POST':
            city = request.form.get('city', 'Philippines')
            categories = request.form.get('category')
            places = get_places_data(city, categories)

            if places:
                return render_template('user/popular.html', places=places, city=city, categories=categories)
            else:
                return 'Error: Failed to fetch places data.'
            return render_template('user/popular.html')
        else:
            city = 'Philippines'
            categories = '12000,19000,16000,17000,10000,13000'
            places = get_places_data(city, categories)
            if places:
                return render_template('user/popular.html', places=places, city=city, categories=categories)
            else:
                return 'Error: Failed to fetch places data.'
        return render_template('user/popular.html')
    return inner()

@bp.route('/popular/<fsq_id>')
def place_info(fsq_id):
    from app.auth import login_required
    @login_required
    def inner():
        place = get_place_data(fsq_id)
        if place:
            return render_template('user/place_info.html', place=place)
        else:
            return 'Error: Failed to fetch place data.'
        return render_template('user/place_info.html')
    return inner()

def get_place_data(fsq_id):
    headers = {
        "accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "fields": 'fsq_id,categories,geocodes,location,name'
    }
    
    db = get_db()

    # Initialize a dictionary to store the details of the place
    place_details = {}

    # Fetch basic details of the place
    details_response = requests.get(FOURSQUARE_API_DETAILS.format(fsq_id=fsq_id), params=params, headers=headers)
    
    if details_response.status_code == 200:
        details = details_response.json()
        
        # Add basic details to the dictionary
        place_details = details
        
        visited_row = db.execute("SELECT 1 FROM visited WHERE fsq_id = ? AND user_id = ?", (fsq_id, g.user['id'])).fetchone()
                
        if visited_row:
            place_details['visited'] = True
        else:
            place_details['visited'] = False
                    
        # Extract latitude and longitude from the place details
        lat = details.get('geocodes', {}).get('main', {}).get('latitude')
        lon = details.get('geocodes', {}).get('main', {}).get('longitude')

        if lat and lon:
            # Fetch photos
            photo_response = requests.get(FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=4", headers=headers)
            if photo_response.status_code == 200:
                photos = photo_response.json()
                place_details['photos'] = photos if photos else []
            else:
                place_details['photos'] = []

            # Fetch weather
            weather_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
            if weather_response.status_code == 200:
                weather = weather_response.json()
                place_details['weather'] = weather
            else:
                place_details['weather'] = {}

            # Fetch tips
            tip_params = {
                'fields': 'text,agree_count,disagree_count,created_at'
            }
            tips_response = requests.get(FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=5", headers=headers, params=tip_params)
            if tips_response.status_code == 200:
                tips = tips_response.json()
                place_details['tips'] = tips if tips else {}
            else:
                place_details['tips'] = {}

        else:
            # Handle the case where lat/lon is missing
            place_details['photos'] = []
            place_details['weather'] = {}
            place_details['tips'] = {}

    else:
        # Log the error or handle it appropriately if details cannot be fetched
        print(f"Error fetching details for fsq_id {fsq_id}, status code: {details_response.status_code}")
        return None

    # Return the complete place details with photos, weather, and tips
    return place_details

@bp.route('/add_visited', methods=('GET', 'POST'))
def add_to_visited():
    from app.auth import login_required
    @login_required
    def inner():
        if request.method == 'POST':
            fsq_id = request.form['place_id']
            error = None
            
            if not fsq_id:
                error = "Error while adding the place. Please try again."
            
            if error is None:
                try:
                    db = get_db()
                    db.execute('INSERT INTO visited (fsq_id, user_id) VALUES (?, ?)', (fsq_id, g.user['id']))
                    db.commit()
                except db.IntegrityError:
                    error = f"The place is already in your visited list."
                else:
                    return redirect(url_for('user.place_info', fsq_id=fsq_id))
            flash(error, 'danger')
        return redirect(url_for('user.place_info', fsq_id=fsq_id))
    return inner()

def get_visited_places_data(visited):
    headers = {
        "accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "fields": 'fsq_id,categories,geocodes,location,name'
    }

    places_details = [] # store the details of each place

    for place in visited:
        place_dict = dict(place)  # Convert place to a dictionary

        fsq_id = place_dict['fsq_id']  
        details_response = requests.get(FOURSQUARE_API_DETAILS.format(fsq_id=fsq_id), params=params, headers=headers)

        if details_response.status_code == 200:
           
            details = details_response.json()
            place_dict.update(details)  # Update the place_dict with details fetched

            lat = place_dict.get('geocodes', {}).get('main', {}).get('latitude')
            lon = place_dict.get('geocodes', {}).get('main', {}).get('longitude')

            if lat and lon:
                # Fetch photos
                photo_response = requests.get(FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=4", headers=headers)
                if photo_response.status_code == 200:
                    photos = photo_response.json()
                    place_dict['photos'] = photos if photos else []
                else:
                    place_dict['photos'] = []

                # Fetch weather
                weather_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
                if weather_response.status_code == 200:
                    weather = weather_response.json()
                    place_dict['weather'] = weather
                else:
                    place_dict['weather'] = {}

                # Fetch tips
                tips_response = requests.get(FOURSQUARE_API_TIPS.format(fsq_id=fsq_id) + "?limit=1", headers=headers)
                if tips_response.status_code == 200:
                    tips = tips_response.json()
                    place_dict['tips'] = tips
                else:
                    place_dict['tips'] = {}

            # Add the place with all the details to the places_details list
            places_details.append(place_dict)
        else:
            places_details.append(None)

    return places_details

@bp.route('/visited', methods=('GET', 'POST'))
def visited():
    from app.auth import login_required
    @login_required
    def inner():
        db = get_db()
        # get all the visited fsq_id in the database table
        visited = db.execute(
            'SELECT fsq_id FROM visited WHERE user_id = ?', (g.user['id'],)
        ).fetchall()
        
        places = get_visited_places_data(visited)
        
        return render_template('user/visited.html', places=places)
    return inner()

@bp.route('/profile', methods=('GET', 'POST'))
def profile():
    from app.auth import login_required
    @login_required
    def inner():
        if request.method == 'POST':
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']
            error = None
            
            if not firstname:
                error = 'First name is required.'
            elif not lastname:
                error = 'Last name is required.'
            elif not email:
                error = 'Email is required.'
           
            if error is None:
                db = get_db()
                db.execute(
                    "UPDATE user SET firstname = ?, lastname = ?, email = ?"
                    " WHERE id = ?",
                    (firstname, lastname, email, g.user['id']),
                )
                db.commit()
                return redirect(url_for("user.profile"))
            
            flash(error)
            return render_template('user/profile.html', user=g.user)
        return render_template('user/profile.html')
    return inner()

@bp.route('/update/character', methods=('GET', 'POST'))
def update_character():
    from app.auth import login_required
    @login_required
    def inner():
        if request.method == 'POST':
            character = request.form['character']
            error = None
            if not character:
                error = 'You need to choose character'
           
            if error is None:
                db = get_db()
                db.execute(
                    "UPDATE user SET character = ?"
                    " WHERE id = ?",
                    (character, g.user['id']),
                )
                db.commit()
                return redirect(url_for("user.profile"))
            
            flash(error)
            return render_template('user/profile.html', user=g.user)
        return render_template('user/profile.html')
    return inner()
