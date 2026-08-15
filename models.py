from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)

    children = db.relationship(
        "Category",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        order_by="Category.name",
    )
    products = db.relationship("Product", backref="category")

    @property
    def is_top_level(self):
        return self.parent_id is None


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_price = db.Column(db.Numeric(10, 2), nullable=True)
    is_featured_hit = db.Column(db.Boolean, nullable=False, default=False)
    is_featured_new = db.Column(db.Boolean, nullable=False, default=False)
    is_featured_sale = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sizes = db.relationship(
        "ProductSize", backref="product", cascade="all, delete-orphan",
        order_by="ProductSize.size",
    )
    photos = db.relationship(
        "ProductPhoto", backref="product", cascade="all, delete-orphan",
        order_by="ProductPhoto.sort_order",
    )

    @property
    def main_photo(self):
        for p in self.photos:
            if p.is_main:
                return p
        return self.photos[0] if self.photos else None

    @property
    def total_stock(self):
        return sum(s.quantity for s in self.sizes)

    @property
    def in_stock_sizes(self):
        return [s for s in self.sizes if s.quantity > 0]

    @property
    def discount_percent(self):
        if not self.discount_price or not self.price:
            return None
        return round(100 - (float(self.discount_price) / float(self.price) * 100))

    @property
    def display_price(self):
        return self.discount_price if self.discount_price else self.price


class ProductSize(db.Model):
    __tablename__ = "product_sizes"
    __table_args__ = (
        db.UniqueConstraint("product_id", "size", name="uq_product_size"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    size = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)


class ProductPhoto(db.Model):
    __tablename__ = "product_photos"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_main = db.Column(db.Boolean, default=False)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(120), nullable=False)
    np_branch = db.Column(db.String(255), nullable=False)
    np_ttn = db.Column(db.String(30), nullable=True)
    status = db.Column(
        db.Enum("new", "processing", "shipped", "completed", "cancelled",
                name="order_status"),
        default="new", nullable=False,
    )
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    @property
    def total(self):
        return sum(float(i.price) * i.quantity for i in self.items)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey("product_sizes.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")
    size = db.relationship("ProductSize")