from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

ROLES = ("buyer", "seller", "admin")
SIZES = ("Small", "Medium", "Large", "Giant")
GENDERS = ("Male", "Female")
DOG_STATUSES = ("available", "reserved", "sold", "hidden")
ORDER_STATUSES = ("pending_payment", "paid", "completed", "cancelled")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(40))
    whatsapp = db.Column(db.String(40))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="buyer")

    # Seller profile / business info
    business_name = db.Column(db.String(160))
    bio = db.Column(db.Text)
    country = db.Column(db.String(80), default="Nigeria")
    state = db.Column(db.String(80))
    city = db.Column(db.String(80))
    address = db.Column(db.String(200))
    avatar = db.Column(db.String(200))

    is_verified = db.Column(db.Boolean, default=False)   # admin-controlled badge
    is_active_user = db.Column(db.Boolean, default=True)  # admin can suspend
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dogs = db.relationship("Dog", backref="seller", lazy="dynamic",
                           cascade="all, delete-orphan", foreign_keys="Dog.seller_id")
    favorites = db.relationship("Favorite", backref="user", lazy="dynamic",
                                cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="buyer", lazy="dynamic",
                             foreign_keys="Order.buyer_id",
                             cascade="all, delete-orphan")

    # ---------- auth helpers ----------
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_active(self):  # Flask-Login uses this to block suspended accounts
        return self.is_active_user

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_seller(self):
        return self.role == "seller"

    @property
    def is_buyer(self):
        return self.role == "buyer"

    @property
    def location(self):
        parts = [p for p in (self.city, self.state, self.country) if p]
        return ", ".join(parts) if parts else "Location not provided"

    @property
    def wa_link(self):
        number = (self.whatsapp or self.phone or "").replace(" ", "").replace("-", "").replace("+", "")
        return f"https://wa.me/{number}" if number else None

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Dog(db.Model):
    __tablename__ = "dogs"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(80), nullable=False)
    breed = db.Column(db.String(80), nullable=False, index=True)
    color = db.Column(db.String(80))
    size = db.Column(db.String(20), default="Medium", index=True)
    gender = db.Column(db.String(10), default="Male")
    age_months = db.Column(db.Integer, default=3)
    weight_kg = db.Column(db.Float)

    price = db.Column(db.Float, nullable=False, default=0)
    negotiable = db.Column(db.Boolean, default=False)
    delivery_available = db.Column(db.Boolean, default=False)

    description = db.Column(db.Text)
    temperament = db.Column(db.String(200))
    health_notes = db.Column(db.String(300))
    vaccinated = db.Column(db.Boolean, default=False)
    dewormed = db.Column(db.Boolean, default=False)
    pedigree = db.Column(db.Boolean, default=False)
    trained = db.Column(db.Boolean, default=False)
    kennel_club_registered = db.Column(db.Boolean, default=False)

    # Location of the animal / seller
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    country = db.Column(db.String(80), default="Nigeria")

    status = db.Column(db.String(20), default="available", index=True)
    is_featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    images = db.relationship("DogImage", backref="dog", lazy="select",
                             cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="dog", lazy="dynamic",
                             cascade="all, delete-orphan")

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img.filename
        return self.images[0].filename if self.images else None

    @property
    def age_label(self):
        if not self.age_months:
            return "Unknown"
        if self.age_months < 12:
            return f"{self.age_months} month{'s' if self.age_months != 1 else ''}"
        years, months = divmod(self.age_months, 12)
        label = f"{years} year{'s' if years != 1 else ''}"
        if months:
            label += f" {months} month{'s' if months != 1 else ''}"
        return label

    @property
    def age_bucket(self):
        if not self.age_months:
            return "Unknown"
        if self.age_months <= 4:
            return "Puppy"
        if self.age_months <= 12:
            return "Young"
        if self.age_months <= 84:
            return "Adult"
        return "Senior"

    @property
    def location(self):
        parts = [p for p in (self.city, self.state, self.country) if p]
        return ", ".join(parts) if parts else "Location not provided"

    @property
    def traits(self):
        """Human-readable checklist of the dog's characteristics."""
        out = []
        if self.vaccinated:
            out.append("Vaccinated")
        if self.dewormed:
            out.append("Dewormed")
        if self.pedigree:
            out.append("Pedigree")
        if self.trained:
            out.append("Trained")
        if self.kennel_club_registered:
            out.append("Kennel club registered")
        if self.delivery_available:
            out.append("Delivery available")
        return out

    def __repr__(self):
        return f"<Dog {self.name} {self.breed}>"


class DogImage(db.Model):
    __tablename__ = "dog_images"

    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey("dogs.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "dog_id", name="uq_fav"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dog_id = db.Column(db.Integer, db.ForeignKey("dogs.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dog = db.relationship("Dog")


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    dog_id = db.Column(db.Integer, db.ForeignKey("dogs.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="pending_payment")
    payment_method = db.Column(db.String(40), default="demo")
    payment_ref = db.Column(db.String(80))

    delivery_address = db.Column(db.String(250))
    buyer_phone = db.Column(db.String(40))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    seller = db.relationship("User", foreign_keys=[seller_id])

    @property
    def status_label(self):
        return self.status.replace("_", " ").title()

    def __repr__(self):
        return f"<Order {self.reference} {self.status}>"


class Inquiry(db.Model):
    """A buyer's message about a specific dog - visible to seller and admin."""

    __tablename__ = "inquiries"

    id = db.Column(db.Integer, primary_key=True)
    dog_id = db.Column(db.Integer, db.ForeignKey("dogs.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dog = db.relationship("Dog")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
