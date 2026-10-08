from flask import (Blueprint, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from .extensions import db
from .helpers import get_or_404, role_required
from .models import Dog, DogImage, GENDERS, Inquiry, Order, SIZES, User
from .uploads import delete_image, save_image

seller_bp = Blueprint("seller", __name__)


# ------------------------------------------------------------------ dashboard
@seller_bp.route("/dashboard")
@role_required("seller")
def dashboard():
    listings = (Dog.query.filter_by(seller_id=current_user.id)
                .order_by(Dog.created_at.desc()).all())

    orders = (Order.query.filter_by(seller_id=current_user.id)
              .order_by(Order.created_at.desc()).all())

    inquiries = (Inquiry.query.filter_by(seller_id=current_user.id)
                 .order_by(Inquiry.created_at.desc()).all())

    revenue = sum(o.amount for o in orders if o.status in ("paid", "completed"))
    stats = {
        "total_dogs": len(listings),
        "available": sum(1 for d in listings if d.status == "available"),
        "sold": sum(1 for d in listings if d.status == "sold"),
        "views": sum(d.views or 0 for d in listings),
        "orders": len(orders),
        "pending_orders": sum(1 for o in orders if o.status == "pending_payment"),
        "revenue": revenue,
        "unread_inquiries": sum(1 for i in inquiries if not i.reply),
        "profile_score": profile_score(current_user),
    }
    return render_template("seller/dashboard.html", listings=listings, orders=orders,
                           inquiries=inquiries, stats=stats)


def profile_score(user):
    """Simple completeness meter shown on the seller dashboard."""
    checks = [bool(user.full_name), bool(user.phone), bool(user.email),
              bool(user.city), bool(user.state), bool(user.bio),
              bool(user.business_name), bool(user.avatar)]
    return round(100 * sum(checks) / len(checks))


# ------------------------------------------------------------------ listings
@seller_bp.route("/dogs/new", methods=["GET", "POST"])
@role_required("seller")
def new_dog():
    if request.method == "POST":
        dog, errors = _save_dog_form(Dog(seller_id=current_user.id))
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("seller/dog_form.html", dog=None, sizes=SIZES,
                                   genders=GENDERS, form=request.form)
        db.session.add(dog)
        db.session.commit()
        _attach_images(dog, request.files.getlist("images"))
        db.session.commit()
        flash("Listing published! It is now visible to buyers.", "success")
        return redirect(url_for("seller.dashboard"))

    return render_template("seller/dog_form.html", dog=None, sizes=SIZES,
                           genders=GENDERS, form={})


@seller_bp.route("/dogs/<int:dog_id>/edit", methods=["GET", "POST"])
@role_required("seller")
def edit_dog(dog_id):
    dog = get_or_404(Dog, dog_id)
    if dog.seller_id != current_user.id:
        abort(403)

    if request.method == "POST":
        _, errors = _save_dog_form(dog, existing=True)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("seller/dog_form.html", dog=dog, sizes=SIZES,
                                   genders=GENDERS, form=request.form)
        _attach_images(dog, request.files.getlist("images"))
        db.session.commit()
        flash("Listing updated.", "success")
        return redirect(url_for("seller.dashboard"))

    return render_template("seller/dog_form.html", dog=dog, sizes=SIZES,
                           genders=GENDERS, form={})


def _save_dog_form(dog, existing=False):
    f = request.form
    errors = []

    name = (f.get("name") or "").strip()
    breed = (f.get("breed") or "").strip()
    if not name:
        errors.append("Dog name is required.")
    if not breed:
        errors.append("Breed is required.")

    try:
        price = float(f.get("price") or 0)
    except ValueError:
        price = 0
        errors.append("Price must be a number.")
    if price <= 0:
        errors.append("Please enter a price greater than zero.")

    try:
        age = int(f.get("age_months") or 0)
    except ValueError:
        age = 0

    try:
        weight = float(f.get("weight_kg")) if f.get("weight_kg") else None
    except ValueError:
        weight = None

    if errors:
        return dog, errors

    dog.name = name
    dog.breed = breed
    dog.color = (f.get("color") or "").strip()
    dog.size = f.get("size") if f.get("size") in SIZES else "Medium"
    dog.gender = f.get("gender") if f.get("gender") in GENDERS else "Male"
    dog.age_months = max(age, 0)
    dog.weight_kg = weight
    dog.price = price
    dog.negotiable = bool(f.get("negotiable"))
    dog.delivery_available = bool(f.get("delivery_available"))
    dog.description = (f.get("description") or "").strip()
    dog.temperament = (f.get("temperament") or "").strip()
    dog.health_notes = (f.get("health_notes") or "").strip()
    dog.vaccinated = bool(f.get("vaccinated"))
    dog.dewormed = bool(f.get("dewormed"))
    dog.pedigree = bool(f.get("pedigree"))
    dog.trained = bool(f.get("trained"))
    dog.kennel_club_registered = bool(f.get("kennel_club_registered"))
    dog.city = (f.get("city") or current_user.city or "").strip()
    dog.state = (f.get("state") or current_user.state or "").strip()
    dog.country = (f.get("country") or current_user.country or "Nigeria").strip()
    dog.status = f.get("status") if f.get("status") in ("available", "reserved", "sold", "hidden") else dog.status or "available"
    return dog, []


def _attach_images(dog, files):
    saved = []
    for file_storage in files:
        path = save_image(file_storage, subfolder="dogs")
        if path:
            saved.append(path)
    if not saved:
        return
    has_primary = any(img.is_primary for img in dog.images)
    for i, path in enumerate(saved):
        db.session.add(DogImage(dog_id=dog.id, filename=path,
                                is_primary=(not has_primary and i == 0)))


@seller_bp.route("/dogs/<int:dog_id>/images/<int:image_id>/delete", methods=["POST"])
@role_required("seller")
def delete_dog_image(dog_id, image_id):
    dog = get_or_404(Dog, dog_id)
    if dog.seller_id != current_user.id:
        abort(403)
    img = get_or_404(DogImage, image_id)
    if img.dog_id != dog.id:
        abort(404)
    delete_image(img.filename)
    db.session.delete(img)
    db.session.commit()
    flash("Photo removed.", "info")
    return redirect(url_for("seller.edit_dog", dog_id=dog.id))


@seller_bp.route("/dogs/<int:dog_id>/set-primary/<int:image_id>", methods=["POST"])
@role_required("seller")
def set_primary_image(dog_id, image_id):
    dog = get_or_404(Dog, dog_id)
    if dog.seller_id != current_user.id:
        abort(403)
    for img in dog.images:
        img.is_primary = (img.id == image_id)
    db.session.commit()
    flash("Cover photo updated.", "success")
    return redirect(url_for("seller.edit_dog", dog_id=dog.id))


@seller_bp.route("/dogs/<int:dog_id>/status", methods=["POST"])
@role_required("seller")
def update_status(dog_id):
    dog = get_or_404(Dog, dog_id)
    if dog.seller_id != current_user.id:
        abort(403)
    status = request.form.get("status")
    if status in ("available", "reserved", "sold", "hidden"):
        dog.status = status
        db.session.commit()
        flash(f"{dog.name} marked as {status}.", "success")
    return redirect(request.referrer or url_for("seller.dashboard"))


@seller_bp.route("/dogs/<int:dog_id>/delete", methods=["POST"])
@role_required("seller")
def delete_dog(dog_id):
    dog = get_or_404(Dog, dog_id)
    if dog.seller_id != current_user.id:
        abort(403)
    for img in dog.images:
        delete_image(img.filename)
    db.session.delete(dog)
    db.session.commit()
    flash("Listing deleted.", "info")
    return redirect(url_for("seller.dashboard"))


# ------------------------------------------------------------------ orders
@seller_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@role_required("seller")
def update_order_status(order_id):
    order = get_or_404(Order, order_id)
    if order.seller_id != current_user.id:
        abort(403)

    status = request.form.get("status")
    if status in ("paid", "completed", "cancelled"):
        order.status = status
        if status == "completed":
            order.dog.status = "sold"
        elif status == "cancelled":
            order.dog.status = "available"
        db.session.commit()
        flash(f"Order {order.reference} marked as {status}.", "success")
    return redirect(url_for("seller.dashboard"))


# ------------------------------------------------------------------ inquiries
@seller_bp.route("/inquiries/<int:inquiry_id>/reply", methods=["POST"])
@role_required("seller")
def reply_inquiry(inquiry_id):
    inq = get_or_404(Inquiry, inquiry_id)
    if inq.seller_id != current_user.id:
        abort(403)
    reply = (request.form.get("reply") or "").strip()
    if len(reply) < 2:
        flash("Please write a reply.", "error")
    else:
        inq.reply = reply
        db.session.commit()
        flash("Reply sent to the buyer.", "success")
    return redirect(url_for("seller.dashboard"))
