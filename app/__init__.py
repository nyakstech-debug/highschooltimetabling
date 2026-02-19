from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    with app.app_context():
        from app.models import School, Teacher, Subject, Class, Lesson, TimeSlot
        db.create_all()
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, school_bp, timetable_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(school_bp)
    app.register_blueprint(timetable_bp)
    
    return app
