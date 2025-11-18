import os
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.menu import MenuItem
from app.services.menu_service import get_menu_item_or_404


# TODO: add unit tests for image upload helpers and attachment logic.
def save_menu_image_local(file: UploadFile) -> str:
    """Persist an uploaded image to the local filesystem."""

    os.makedirs(settings.MEDIA_LOCAL_DIR, exist_ok=True)
    _, ext = os.path.splitext(file.filename or "")
    ext = ext or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.MEDIA_LOCAL_DIR, filename)

    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())

    # TODO: serve local media via a proper static files mechanism.
    return f"/static/menu/{filename}"


def save_menu_image_s3(file: UploadFile) -> str:
    """Upload an image to S3 and return the public URL."""

    # TODO: implement real S3 uploads via boto3 client with signed URLs.
    raise NotImplementedError("S3 upload not implemented yet")


def upload_menu_image(file: UploadFile) -> str:
    """Upload an image using the configured backend."""

    if settings.MEDIA_STORAGE.lower() == "s3":
        return save_menu_image_s3(file)
    return save_menu_image_local(file)


def attach_image_to_menu_item(
    db: Session,
    item_id: int,
    image_url: str,
) -> MenuItem:
    """Persist an image URL onto a menu item."""

    item = get_menu_item_or_404(db, item_id)
    item.image_url = image_url
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
