from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User
from .uploads import save_image

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_router"))

    if request.method == "POST":
        f = request.form
        full_name = (f.get("full_name") or "").strip()
        email = (f.get("email") or "").strip().lower()
        password = f.get("password") or ""
        confirm = f.get("confirm") or ""
        role = f.get("role") if f.get("role") in ("buyer", "seller") else "buyer"

        errors = []
        if len(full_name) < 3:
            errors.append("Please enter your full name.")
        if "@" not in email or "." not in email:
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", form=f, role=role)

        user = User(
            full_name=full_name,
            email=email,
            role=role,
            phone=(f.get("phone") or "").strip(),
            whatsapp=(f.get("whatsapp") or "").strip(),
            city=(f.get("city") or "").strip(),
            state=(f.get("state") or "").strip(),
            country=(f.get("country") or "Nigeria").strip(),
            business_name=(f.get("business_name") or "").strip(),
            bio=(f.get("bio") or "").strip(),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to PawMarket, {user.full_name.split()[0]}!", "success")
        return redirect(url_for("main.dashboard_router"))

    role = request.args.get("role", "buyer")
    return render_template("auth/register.html", form={}, role=role)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard_router"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active_user:
                flash("Your account has been suspended. Please contact support.", "error")
                return render_template("auth/login.html")
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.full_name.split()[0]}!", "success")
            nxt = request.args.get("next")
            if nxt and nxt.startswith("/"):
                return redirect(nxt)
            return redirect(url_for("main.dashboard_router"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        f = request.form
        current_user.full_name = (f.get("full_name") or current_user.full_name).strip()
        current_user.phone = (f.get("phone") or "").strip()
        current_user.whatsapp = (f.get("whatsapp") or "").strip()
        current_user.business_name = (f.get("business_name") or "").strip()
        current_user.bio = (f.get("bio") or "").strip()
        current_user.address = (f.get("address") or "").strip()
        current_user.city = (f.get("city") or "").strip()
        current_user.state = (f.get("state") or "").strip()
        current_user.country = (f.get("country") or "Nigeria").strip()

        avatar = save_image(request.files.get("avatar"), subfolder="avatars")
        if avatar:
            current_user.avatar = avatar

        new_password = f.get("new_password") or ""
        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "error")
                return redirect(url_for("auth.profile"))
            if not current_user.check_password(f.get("current_password") or ""):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("auth.profile"))
            current_user.set_password(new_password)

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")
