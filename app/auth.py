import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.db import get_db
from app.user import index
from . import *
from flask_mail import Message

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('POST', 'GET'))
def register():  
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
            
        if not firstname:
            error = 'First name is required.'
        elif not lastname:
            error = 'Last name is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        
        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (firstname, lastname, email, password) VALUES (?, ?, ?, ?)",
                    (firstname, lastname, email, generate_password_hash(password)),
                )
                db.commit()
                      
                token = s.dumps(email, salt='email-confirm')
                
                msg = Message(
                    'Email Verification - City Explorer', 
                    recipients=[email]
                )
                link = url_for('auth.confirm', token=token, _external=True)
                msg.body = f'Hi {firstname}\nPlease click the link to verify your email: {link}'
                
                # Send the email
                try:
                    mail.send(msg)  
                    flash('A verification email has been sent to your email address!', 'info')
                except Exception as e:
                    flash(f'Failed to send email. Error: {e}', 'danger')
                    return redirect(url_for('auth.register'))
        
            except db.IntegrityError:
                error = f"{email} is already registered."
            else:
                return redirect(url_for("auth.login"))  
        flash(error, 'danger')        
    return render_template('auth/register.html')

@bp.route('/confirm/<token>')
def confirm(token):
    try:
        # validate
        email = s.loads(token, salt='email-confirm', max_age=3600)  # Token is valid for 1hr
    except SignatureExpired:
        return '<h1>The token is expired!</h1>'
    
    user = get_db().execute(
        'SELECT * FROM user WHERE email = ?', (email,)
    ).fetchone()
    
    if user:
        get_db().execute(
            'UPDATE user SET verified = "true" WHERE email = ?', (email,)
        )
        get_db().commit()
    else:
        return '<h1>Invalid token</h1>'
    
    flash('Your email has been verified successfully!', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE email = ?', (email,)
        ).fetchone()
        
        if user is None:
            error = "Email don't exist."
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('user.index'))
        
        flash(error, 'danger')
        
    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        
        if g.user['verified'] == 'false':  #ensures that the user has verified their email
            flash('Please verify your email before accessing this page.', 'warning')
            return redirect(url_for('auth.register'))
        
        return view(**kwargs)
    return wrapped_view