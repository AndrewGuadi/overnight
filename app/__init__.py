from flask import Flask
from .config      import Config
from .extensions  import db, migrate, login_manager
from .auth.routes import auth_bp
from .main.routes import main_bp

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
