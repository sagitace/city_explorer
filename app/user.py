from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from app.db import get_db
import requests

bp = Blueprint('user', __name__, url_prefix='/user')

FOURSQUARE_API_URL = "https://api.foursquare.com/v3/places/search"
FOURSQUARE_API_KEY = "fsq3XflsHeDs8cP703mPhp/K64ZuJYHFra2NGkn+SmjbPZM="
FOURSQUARE_API_PHOTOS_URL = "https://api.foursquare.com/v3/places/{fsq_id}/photos"

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
        
    if city or categories:
        params["limit"] = 6
        response = requests.get(FOURSQUARE_API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            places = response.json().get('results', [])
            for place in places:
                fsq_id = place.get('fsq_id')
                photo_response = requests.get(FOURSQUARE_API_PHOTOS_URL.format(fsq_id=fsq_id) + "?limit=1", headers=headers)
                if photo_response.status_code == 200:
                    photos = photo_response.json()  # return a list
                    place['photos'] = photos if photos else []  # Add the list of photos if it exists
                else:
                    place['photos'] = []
            return places  # Return JSON data from the API
        else:
            return None  # Handle error if API call fails
    
@bp.route('/', methods=('GET', 'POST'))
def index():
    from app.auth import login_required
    @login_required
    def inner():
        if request.method == 'POST':
            city = request.form.get('city', 'Philippines')
            categories = request.form.get('category')
            places = get_places_data(city, categories)
        
            if places:
                return render_template('user/index.html', places=places, city=city, categories=categories)
            else:
                return 'Error: Failed to fetch places data.'
            return render_template('user/index.html')
        else:
            city = 'Philippines'
            categories = '12000,19000,16000,17000,10000,13000'
            places = get_places_data(city, categories)
            if places:
                return render_template('user/index.html', places=places, city=city, categories=categories)
            else:
                return 'Error: Failed to fetch places data.'
        return render_template('user/index.html')
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


