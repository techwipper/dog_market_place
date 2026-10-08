import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration for PawMarket."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'pawmarket.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads" / "dogs"
    PROFILE_UPLOAD_FOLDER = BASE_DIR / "static" / "uploads" / "avatars"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # Business rules
    CURRENCY = "\u20a6"          # Naira
    CURRENCY_CODE = "NGN"
    SITE_NAME = "PawMarket"
    CONTACT_EMAIL = "hello@pawmarket.ng"

    # Payments (demo gateway - swap for Paystack/Flutterwave in production)
    PAYMENT_MODE = os.environ.get("PAYMENT_MODE", "demo")
    PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
    FLUTTERWAVE_PUBLIC_KEY = os.environ.get("FLUTTERWAVE_PUBLIC_KEY", "")

    DOGS_PER_PAGE = 9
