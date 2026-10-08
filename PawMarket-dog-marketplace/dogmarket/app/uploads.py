import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


def allowed_image(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_image(file_storage, subfolder="dogs"):
    """Persist an uploaded image and return its path relative to /static/uploads."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_image(file_storage.filename):
        return None

    safe = secure_filename(file_storage.filename)
    stem = os.path.splitext(safe)[0][:40] or "image"
    unique = f"{stem}-{uuid.uuid4().hex[:10]}{os.path.splitext(safe)[1].lower()}"

    base = current_app.config["UPLOAD_FOLDER" if subfolder == "dogs" else "PROFILE_UPLOAD_FOLDER"]
    os.makedirs(base, exist_ok=True)
    file_storage.save(os.path.join(base, unique))
    return f"{subfolder}/{unique}"


def delete_image(rel_path):
    if not rel_path:
        return
    full = os.path.join(current_app.static_folder, "uploads", rel_path)
    try:
        if os.path.isfile(full):
            os.remove(full)
    except OSError:
        pass
