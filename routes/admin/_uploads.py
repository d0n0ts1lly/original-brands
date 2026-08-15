import os
import uuid

from flask import current_app

ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp", "gif"}


def save_uploaded_photo(file_storage, subfolder):
    """Зберігає файл у static/uploads/<subfolder> і повертає публічний шлях."""
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_PHOTO_EXT:
        return None, f"Непідтримуваний формат файлу «{filename}»"

    upload_dir = os.path.join(current_app.root_path, "static", "uploads", subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(upload_dir, stored_name))
    return f"/static/uploads/{subfolder}/{stored_name}", None


def delete_uploaded_photo(url):
    if url and url.startswith("/static/uploads/"):
        full = os.path.join(current_app.root_path, url.lstrip("/"))
        if os.path.exists(full):
            os.remove(full)