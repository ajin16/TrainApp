import os
from flask import Flask
from config import Config
from models import db, User, Station, Train, Booking
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

import os
from datetime import datetime, date, timedelta, time
import click
from flask import Flask
from flask_migrate import Migrate
from config import Config
from models import db, User, Station, Train, Booking
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

migrate = Migrate()

def create_app(test_config=None, testing=False):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if testing or app.config.get('TESTING'):
        app.config['TESTING'] = True

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        now = datetime.now()
        is_tatkal_open = now.time() >= time(10, 0)
        return {
            'all_stations': Station.query.order_by(Station.name).all() if db.engine else [],
            'server_now': now,
            'is_tatkal_open': is_tatkal_open,
            'tatkal_open_time_str': '10:00 AM',
            'arp_max_days': 14,
            'max_journey_date': (date.today() + timedelta(days=14)).strftime('%Y-%m-%d'),
            'tomorrow_date_str': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        }

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%d-%b-%Y %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)

    @app.cli.command('archive-transactions')
    @click.option('--days', default=5, help='Number of retention days (default: 5)')
    @click.option('--purge', is_flag=True, default=False, help='Permanently delete instead of marking as archived')
    def archive_transactions_command(days, purge):
        """Retention Job: Archive or purge transaction records older than N days."""
        from services.booking_service import archive_or_purge_old_transactions
        count = archive_or_purge_old_transactions(retention_days=days, purge=purge)
        action = "Permanently purged" if purge else "Archived"
        click.echo(f"Retention Job: {action} {count} transactions older than {days} days.")

    @app.cli.command('auto-chart')
    @click.option('--hours', default=12, help='Hours before origin departure (default: 12)')
    def auto_chart_command(hours):
        """Automated Charting: Trigger reservation charts for trains within N hours of departure."""
        from services.chart_service import check_and_auto_prepare_charts
        res = check_and_auto_prepare_charts(hours_before=hours)
        click.echo(f"Auto-Charting Completed: Generated {res['count']} reservation chart(s).")

    with app.app_context():
        # Safe table creation for uninitialized databases or local SQLite
        db.create_all()
        # Safe idempotent startup initialization:
        # Only seeds if database is completely uninitialized and not in test mode
        if not app.config.get('TESTING') and os.environ.get('AUTO_SEED', '1') == '1':
            from seed_data import seed_if_empty
            seed_if_empty(app)

    # Start automated background charting daemon (checks every 60s for trains 12h before departure)
    if not app.config.get('TESTING') and os.environ.get('DISABLE_AUTO_CHART', '0') != '1':
        _start_auto_chart_daemon(app)

    return app

def _start_auto_chart_daemon(app):
    """Background daemon thread to automatically create charts 12 hours before train departures."""
    import threading
    import time

    def daemon_loop():
        # Small initial delay to allow server initialization
        time.sleep(5)
        while True:
            try:
                with app.app_context():
                    from services.chart_service import check_and_auto_prepare_charts
                    check_and_auto_prepare_charts(hours_before=12)
            except Exception:
                pass
            time.sleep(60)  # Check every 60 seconds

    daemon_thread = threading.Thread(target=daemon_loop, daemon=True, name="AutoChartDaemon")
    daemon_thread.start()

# Gunicorn entry point  (gunicorn "app:app")
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(debug=debug, host='0.0.0.0', port=port)
