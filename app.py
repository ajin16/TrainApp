import os
from flask import Flask
from config import Config
from models import db, User, Station, Train, Booking
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        return {
            'all_stations': Station.query.order_by(Station.name).all() if db.engine else []
        }

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%d-%b-%Y %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)

    with app.app_context():
        db.create_all()

    return app

# Gunicorn entry point  (gunicorn "app:app")
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(debug=debug, host='0.0.0.0', port=port)
