import click
from flask import Flask, session

from config import Config
from models import Category, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from routes.main import main_bp
    from routes.catalog import catalog_bp
    from routes.product import product_bp
    from routes.checkout import checkout_bp
    from routes.pages import pages_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.novaposhta import novaposhta_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix="/admin")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(novaposhta_bp)

    @app.context_processor
    def inject_globals():
        nav_categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
        cart_count = sum(session.get("cart", {}).values())
        is_admin = "admin_id" in session
        return dict(nav_categories=nav_categories, cart_count=cart_count, is_admin=is_admin)

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        """Створити користувача для входу в /admin/login."""
        from werkzeug.security import generate_password_hash

        from models import AdminUser

        if AdminUser.query.filter_by(username=username).first():
            click.echo(f"Користувач «{username}» вже існує")
            return

        user = AdminUser(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        click.echo(f"Адміністратора «{username}» створено")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)