from flask import Flask, render_template, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import current_user
from config import Config
from models import db, bcrypt, login_manager

# Initialize CSRF protection
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app context
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
        
    # Register blueprints
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from wellness import wellness as wellness_blueprint
    app.register_blueprint(wellness_blueprint)
    
    from admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    # Home landing page route
    @app.route('/')
    def home():
        # Redirect to dashboard if logged in, otherwise show landing page
        if current_user.is_authenticated:
            if current_user.role in ['admin', 'counselor']:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('wellness.dashboard'))
        return render_template('index.html')
        
    # 404 Error Handler
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=app.config['DEBUG'])