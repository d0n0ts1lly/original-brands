from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models import AdminUser

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = AdminUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["admin_id"] = user.id
            session["admin_username"] = user.username
            flash(f"Вітаємо, {user.username}!", "success")
            next_url = request.args.get("next") or url_for("admin.products_list")
            return redirect(next_url)

        flash("Невірний логін або пароль", "error")

    return render_template("admin/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Ви вийшли з адмін-панелі", "success")
    return redirect(url_for("auth.login"))