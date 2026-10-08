from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from .extensions import db
from .helpers import get_or_404, role_required
from .models import Dog, Inquiry, Order, User
from .uploads import delete_image

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@role_required("admin")
def dashboard():
    sellers = (User.query.filter_by(role="seller")
               .order_by(User.created_at.desc()).all())
    buyers = User.query.filter_by(role="buyer").count()

    # per-seller activity: listings + orders + contact completeness
    seller_rows = []
    for s in sellers:
        seller_rows.append({
            "user": s,
            "listings": s.dogs.count(),
            "available": s.dogs.filter(Dog.status == "available").count(),
            "sold": s.dogs.filter(Dog.status == "sold").count(),
            "orders": Order.query.filter_by(seller_id=s.id).count(),
            "revenue": db.session.query(func.coalesce(func.sum(Order.amount), 0))
                       .filter(Order.seller_id == s.id,
                               Order.status.in_(("paid", "completed"))).scalar(),
            "has_contact": bool(s.phone or s.whatsapp),
            "has_location": bool(s.city or s.state),
            "missing": [label for label, ok in (
                ("phone", bool(s.phone)),
                ("whatsapp", bool(s.whatsapp)),
                ("city", bool(s.city)),
                ("state", bool(s.state)),
                ("bio", bool(s.bio)),
            ) if not ok],
        })

    stats = {
        "users": User.query.count(),
        "sellers": len(sellers),
        "buyers": buyers,
        "dogs": Dog.query.count(),
        "available": Dog.query.filter_by(status="available").count(),
        "sold": Dog.query.filter_by(status="sold").count(),
        "orders": Order.query.count(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.amount), 0))
                   .filter(Order.status.in_(("paid", "completed"))).scalar(),
        "unverified": User.query.filter_by(role="seller", is_verified=False).count(),
        "suspended": User.query.filter_by(is_active_user=False).count(),
        "inquiries": Inquiry.query.count(),
    }

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    recent_dogs = Dog.query.order_by(Dog.created_at.desc()).limit(6).all()

    return render_template("admin/dashboard.html", seller_rows=seller_rows, stats=stats,
                           recent_orders=recent_orders, recent_dogs=recent_dogs)


@admin_bp.route("/sellers")
@role_required("admin")
def sellers():
    status = request.args.get("status")
    q = User.query.filter_by(role="seller")
    if status == "verified":
        q = q.filter_by(is_verified=True)
    elif status == "unverified":
        q = q.filter_by(is_verified=False)
    elif status == "suspended":
        q = q.filter_by(is_active_user=False)
    rows = q.order_by(User.created_at.desc()).all()
    return render_template("admin/sellers.html", sellers=rows, status=status)


@admin_bp.route("/sellers/<int:seller_id>")
@role_required("admin")
def seller_detail(seller_id):
    seller = get_or_404(User, seller_id)
    dogs = seller.dogs.order_by(Dog.created_at.desc()).all()
    orders = Order.query.filter_by(seller_id=seller.id).order_by(Order.created_at.desc()).all()
    inquiries = (Inquiry.query.filter_by(seller_id=seller.id)
                 .order_by(Inquiry.created_at.desc()).all())
    revenue = sum(o.amount for o in orders if o.status in ("paid", "completed"))
    return render_template("admin/seller_detail.html", seller=seller, dogs=dogs,
                           orders=orders, inquiries=inquiries, revenue=revenue)


@admin_bp.route("/users/<int:user_id>/verify", methods=["POST"])
@role_required("admin")
def toggle_verify(user_id):
    user = get_or_404(User, user_id)
    user.is_verified = not user.is_verified
    db.session.commit()
    flash(f"{user.full_name} is now {'verified' if user.is_verified else 'unverified'}.", "success")
    return redirect(request.referrer or url_for("admin.sellers"))


@admin_bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@role_required("admin")
def toggle_suspend(user_id):
    user = get_or_404(User, user_id)
    if user.is_admin:
        flash("Admin accounts can't be suspended.", "error")
        return redirect(request.referrer or url_for("admin.sellers"))
    user.is_active_user = not user.is_active_user
    db.session.commit()
    flash(f"{user.full_name} has been {'reactivated' if user.is_active_user else 'suspended'}.",
          "success")
    return redirect(request.referrer or url_for("admin.sellers"))


@admin_bp.route("/dogs")
@role_required("admin")
def dogs():
    status = request.args.get("status")
    seller_id = request.args.get("seller_id", type=int)
    q = Dog.query
    if status:
        q = q.filter(Dog.status == status)
    if seller_id:
        q = q.filter(Dog.seller_id == seller_id)
    rows = q.order_by(Dog.created_at.desc()).all()
    return render_template("admin/dogs.html", dogs=rows, status=status, seller_id=seller_id)


@admin_bp.route("/dogs/<int:dog_id>/feature", methods=["POST"])
@role_required("admin")
def toggle_feature(dog_id):
    dog = get_or_404(Dog, dog_id)
    dog.is_featured = not dog.is_featured
    db.session.commit()
    flash(f"{dog.name} {'featured on the homepage' if dog.is_featured else 'unfeatured'}.", "success")
    return redirect(request.referrer or url_for("admin.dogs"))


@admin_bp.route("/dogs/<int:dog_id>/status", methods=["POST"])
@role_required("admin")
def set_dog_status(dog_id):
    dog = get_or_404(Dog, dog_id)
    status = request.form.get("status")
    if status in ("available", "reserved", "sold", "hidden"):
        dog.status = status
        db.session.commit()
        flash(f"{dog.name} set to {status}.", "success")
    return redirect(request.referrer or url_for("admin.dogs"))


@admin_bp.route("/dogs/<int:dog_id>/delete", methods=["POST"])
@role_required("admin")
def delete_dog(dog_id):
    dog = get_or_404(Dog, dog_id)
    for img in dog.images:
        delete_image(img.filename)
    db.session.delete(dog)
    db.session.commit()
    flash("Listing removed.", "info")
    return redirect(url_for("admin.dogs"))


@admin_bp.route("/orders")
@role_required("admin")
def orders():
    status = request.args.get("status")
    q = Order.query
    if status:
        q = q.filter(Order.status == status)
    rows = q.order_by(Order.created_at.desc()).all()
    revenue = sum(o.amount for o in rows if o.status in ("paid", "completed"))
    return render_template("admin/orders.html", orders=rows, status=status, revenue=revenue)


@admin_bp.route("/users")
@role_required("admin")
def users():
    role = request.args.get("role")
    q = User.query
    if role in ("buyer", "seller", "admin"):
        q = q.filter(User.role == role)
    rows = q.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=rows, role=role)
