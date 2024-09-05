import os

from flask import Flask, render_template, redirect, url_for, g

def create_app():
    # create and configure appp
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
    )
    
    #
    app.config.from_pyfile('config.py', silent=True)
   
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    @app.route('/')
    def index():
        if g.user is not None:
            return redirect(url_for('user.index'))
        return render_template('index.html')
    
    from . import db
    db.init_app(app)
    
    from . import auth
    app.register_blueprint(auth.bp)

    from . import user
    app.register_blueprint(user.bp)
    app.add_url_rule('/', endpoint='index')
    
    return app