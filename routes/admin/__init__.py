
from flask import Blueprint, redirect, request, session, url_for
 
admin_bp = Blueprint("admin", __name__, template_folder="../../templates/admin")
 
 
@admin_bp.before_request
def require_login():
    if "admin_id" not in session:
        return redirect(url_for("auth.login", next=request.path))
 
 
@admin_bp.route("/")
def dashboard():
    return redirect(url_for("admin.products_list"))
 
 
# Підмодулі реєструють свої роути на admin_bp при імпорті.
from . import products, categories, orders  # noqa: E402,F401
 