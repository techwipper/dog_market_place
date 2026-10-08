import random
import string
from datetime import datetime

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from .extensions import db
from .helpers import get_or_404
from .models import Dog, Favorite, Inquiry, Order, SIZES, User

main_bp = Blueprint("main", __name__)


# ------------------------------------------------------------------ helpers
def _order_reference():
    return "PM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _dog_filters(args):
    """Build the browse-page query from request args."""
    q = Dog.query.filter(Dog.status.in_(("available", "reserved")))

    search = (args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Dog.name.ilike(like), Dog.breed.ilike(like),
                         Dog.color.ilike(like), Dog.city.ilike(like),
                         Dog.state.ilike(like), Dog.description.ilike(like)))

    breed = args.get("breed")
    if breed:
        q = q.filter(Dog.breed == breed)

    size = args.get("size")
    if size in SIZES:
        q = q.filter(Dog.size == size)

    gender = args.get("gender")
    if gender in ("Male", "Female"):
        q = q.filter(Dog.gender == gender)

    color = (args.get("color") or "").strip()
    if color:
        q = q.filter(Dog.color.ilike(f"%{color}%"))

    location = (args.get("location") or "").strip()
    if location:
        q = q.filter(or_(Dog.state.ilike(f"%{location}%"), Dog.city.ilike(f"%{location}%")))

    age = args.get("age")
    if age == "puppy":
        q = q.filter(Dog.age_months <= 4)
    elif age == "young":
        q = q.filter(Dog.age_months > 4, Dog.age_months <= 12)
    elif age == "adult":
        q = q.filter(Dog.age_months > 12)

    min_price = args.get("min_price", type=float)
    if min_price:
        q = q.filter(Dog.price >= min_price)
    max_price = args.get("max_price", type=float)
    if max_price:
        q = q.filter(Dog.price <= max_price)

    if args.get("vaccinated") == "1":
        q = q.filter(Dog.vaccinated.is_(True))
    if args.get("delivery") == "1":
        q = q.filter(Dog.delivery_available.is_(True))
    if args.get("pedigree") == "1":
        q = q.filter(Dog.pedigree.is_(True))

    sort = args.get("sort", "newest")
    if sort == "price_low":
        q = q.order_by(Dog.price.asc())
    elif sort == "price_high":
        q = q.order_by(Dog.price.desc())
    elif sort == "popular":
        q = q.order_by(Dog.views.desc(), Dog.created_at.desc())
    else:
        q = q.order_by(Dog.is_featured.desc(), Dog.created_at.desc())
    return q


# ------------------------------------------------------------------ public
@main_bp.route("/")
def home():
    featured = (Dog.query.filter_by(status="available")
                .order_by(Dog.is_featured.desc(), Dog.created_at.desc()).limit(6).all())

    breeds = (db.session.query(Dog.breed, func.count(Dog.id))
              .filter(Dog.status == "available")
              .group_by(Dog.breed).order_by(func.count(Dog.id).desc()).limit(8).all())

    stats = {
        "dogs": Dog.query.filter_by(status="available").count(),
        "sellers": User.query.filter_by(role="seller").count(),
        "states": db.session.query(func.count(func.distinct(Dog.state))).scalar() or 0,
        "sold": Order.query.filter(Order.status.in_(("paid", "completed"))).count(),
    }
    return render_template("home.html", featured=featured, breeds=breeds, stats=stats)


@main_bp.route("/dogs")
def browse():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["DOGS_PER_PAGE"]
    pagination = _dog_filters(request.args).paginate(page=page, per_page=per_page, error_out=False)

    breeds = [b for (b,) in db.session.query(Dog.breed).distinct().order_by(Dog.breed).all()]
    states = [s for (s,) in db.session.query(Dog.state).distinct()
              .filter(Dog.state.isnot(None)).order_by(Dog.state).all()]

    favorite_ids = set()
    if current_user.is_authenticated:
        favorite_ids = {f.dog_id for f in current_user.favorites}

    page_args = {k: v for k, v in request.args.items() if k != "page"}

    return render_template("browse.html", pagination=pagination, dogs=pagination.items,
                           breeds=breeds, states=states, sizes=SIZES,
                           favorite_ids=favorite_ids, args=request.args,
                           page_args=page_args)


@main_bp.route("/dogs/<int:dog_id>")
def dog_detail(dog_id):
    dog = get_or_404(Dog, dog_id)
    seller = dog.seller

    # only the owner or an admin may view hidden/sold-from-catalog listings
    privileged = current_user.is_authenticated and (
        current_user.id == seller.id or current_user.is_admin)
    if dog.status == "hidden" and not privileged:
        abort(404)

    dog.views = (dog.views or 0) + 1
    db.session.commit()

    related = (Dog.query.filter(Dog.breed == dog.breed, Dog.id != dog.id,
                                Dog.status == "available")
               .order_by(Dog.created_at.desc()).limit(3).all())

    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(user_id=current_user.id, dog_id=dog.id).first() is not None

    seller_stats = {
        "listings": seller.dogs.filter(Dog.status == "available").count(),
        "total": seller.dogs.count(),
        "member_since": seller.created_at,
    }
    return render_template("dog_detail.html", dog=dog, seller=seller, related=related,
                           is_favorite=is_favorite, can_view_contact=current_user.is_authenticated,
                           seller_stats=seller_stats)


@main_bp.route("/sellers/<int:seller_id>")
def seller_profile(seller_id):
    seller = get_or_404(User, seller_id)
    dogs = (seller.dogs.filter(Dog.status == "available")
            .order_by(Dog.created_at.desc()).all())
    return render_template("seller_profile.html", seller=seller, dogs=dogs)


@main_bp.route("/favorites/toggle/<int:dog_id>", methods=["POST"])
@login_required
def toggle_favorite(dog_id):
    dog = get_or_404(Dog, dog_id)
    fav = Favorite.query.filter_by(user_id=current_user.id, dog_id=dog.id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash(f"{dog.name} removed from your saved list.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, dog_id=dog.id))
        db.session.commit()
        flash(f"{dog.name} saved to your list.", "success")
    return redirect(request.referrer or url_for("main.browse"))


@main_bp.route("/dogs/<int:dog_id>/inquire", methods=["POST"])
@login_required
def inquire(dog_id):
    dog = get_or_404(Dog, dog_id)
    message = (request.form.get("message") or "").strip()
    if len(message) < 5:
        flash("Please write a short message to the seller.", "error")
        return redirect(url_for("main.dog_detail", dog_id=dog.id))

    db.session.add(Inquiry(dog_id=dog.id, buyer_id=current_user.id,
                           seller_id=dog.seller_id, message=message))
    db.session.commit()
    flash("Message sent to the seller. You'll see replies in your dashboard.", "success")
    return redirect(url_for("main.dog_detail", dog_id=dog.id))


# ------------------------------------------------------------------ checkout
@main_bp.route("/checkout/<int:dog_id>", methods=["GET", "POST"])
@login_required
def checkout(dog_id):
    dog = get_or_404(Dog, dog_id)
    if dog.status == "sold":
        flash("Sorry, this dog has already been sold.", "error")
        return redirect(url_for("main.dog_detail", dog_id=dog.id))
    if dog.seller_id == current_user.id:
        flash("You can't buy your own listing.", "error")
        return redirect(url_for("main.dog_detail", dog_id=dog.id))

    if request.method == "POST":
        order = Order(
            reference=_order_reference(),
            dog_id=dog.id,
            buyer_id=current_user.id,
            seller_id=dog.seller_id,
            amount=dog.price,
            status="pending_payment",
            payment_method=request.form.get("payment_method", "demo"),
            delivery_address=(request.form.get("delivery_address") or "").strip(),
            buyer_phone=(request.form.get("buyer_phone") or "").strip(),
            notes=(request.form.get("notes") or "").strip(),
        )
        db.session.add(order)
        db.session.commit()
        return redirect(url_for("main.order_detail", order_id=order.id))

    return render_template("checkout.html", dog=dog)


@main_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = get_or_404(Order, order_id)
    if current_user.id not in (order.buyer_id, order.seller_id) and not current_user.is_admin:
        abort(403)
    return render_template("order_detail.html", order=order)


@main_bp.route("/orders/<int:order_id>/pay", methods=["POST"])
@login_required
def pay_order(order_id):
    """Demo payment step.

    In production, replace this handler with a Paystack/Flutterwave
    initialise + webhook verification flow.
    """
    order = get_or_404(Order, order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status != "pending_payment":
        flash("This order has already been processed.", "info")
        return redirect(url_for("main.order_detail", order_id=order.id))

    order.status = "paid"
    order.payment_ref = "DEMO-" + "".join(random.choices(string.digits, k=10))
    order.dog.status = "reserved"
    db.session.commit()

    flash("Payment confirmed (demo gateway). The seller has been notified to arrange handover.",
          "success")
    return redirect(url_for("main.order_detail", order_id=order.id))


@main_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = get_or_404(Order, order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status in ("paid", "completed"):
        flash("Paid orders can't be cancelled here - contact the seller.", "error")
        return redirect(url_for("main.order_detail", order_id=order.id))

    order.status = "cancelled"
    if order.dog.status == "reserved":
        order.dog.status = "available"
    db.session.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("main.dashboard_router"))


@main_bp.route("/orders/<int:order_id>/receipt")
@login_required
def receipt(order_id):
    order = get_or_404(Order, order_id)
    if current_user.id not in (order.buyer_id, order.seller_id) and not current_user.is_admin:
        abort(403)
    return render_template("receipt.html", order=order, now=datetime.utcnow())


# ------------------------------------------------------------------ dashboards
@main_bp.route("/dashboard")
@login_required
def dashboard_router():
    """Send each role to the right dashboard (buyers keep their own page)."""
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    if current_user.is_seller:
        return redirect(url_for("seller.dashboard"))
    return redirect(url_for("main.buyer_dashboard"))


@main_bp.route("/buyer/dashboard")
@login_required
def buyer_dashboard():
    orders = (Order.query.filter_by(buyer_id=current_user.id)
              .order_by(Order.created_at.desc()).all())
    favorites = (Favorite.query.filter_by(user_id=current_user.id)
                 .order_by(Favorite.created_at.desc()).all())
    inquiries = (Inquiry.query.filter_by(buyer_id=current_user.id)
                 .order_by(Inquiry.created_at.desc()).all())

    spent = sum(o.amount for o in orders if o.status in ("paid", "completed"))
    return render_template("buyer_dashboard.html", orders=orders, favorites=favorites,
                           inquiries=inquiries, spent=spent,
                           dog_count=Dog.query.filter_by(status="available").count())
