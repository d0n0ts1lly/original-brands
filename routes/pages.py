from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/about")
def about():
    return render_template("pages/about.html")


@pages_bp.route("/delivery")
def delivery():
    return render_template("pages/delivery.html")


@pages_bp.route("/size-guide")
def size_guide():
    return render_template("pages/size_guide.html")


@pages_bp.route("/how-to-order")
def how_to_order():
    return render_template("pages/how_to_order.html")


@pages_bp.route("/returns")
def returns():
    return render_template("pages/returns.html")