from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_validation import detect_mime, extension_for, validate_mime
from app.core.config import settings
from app.models.document import Document, DocumentDirection, DocumentStatus


class DocumentValidationError(ValueError):
    pass


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_image_preview(content: bytes, extension: str, preview_dir: Path, stem: str) -> str | None:
    if extension not in {"jpg", "jpeg", "png", "gif", "bmp", "webp"}:
        return None
    try:
        from PIL import Image

        image_path = preview_dir / f"{stem}.jpg"
        with Image.open(BytesIO(content)) as image:
            preview = image.convert("RGB")
            preview.thumbnail((320, 320))
            preview.save(image_path, format="JPEG", quality=85)
        return str(image_path.relative_to(upload_root()))
    except Exception as exc:
        raise DocumentValidationError("Файл изображения повреждён") from exc


async def save_upload(upload: UploadFile, user_id: UUID, direction: DocumentDirection) -> Document:
    original_name = upload.filename or "unnamed"
    try:
        extension = extension_for(original_name)
    except ValueError as exc:
        raise DocumentValidationError(str(exc)) from exc

    content = await upload.read(settings.max_file_size + 1)
    if len(content) > settings.max_file_size:
        raise DocumentValidationError("Файл слишком большой (макс. 50MB)")
    if not content:
        raise DocumentValidationError("Файл пустой или повреждён")

    try:
        mime_type = detect_mime(content)
        validate_mime(extension, mime_type)
    except (RuntimeError, ValueError) as exc:
        raise DocumentValidationError(str(exc)) from exc

    now = date.today()
    relative_dir = Path(f"{now.year:04d}") / f"{now.month:02d}" / f"{now.day:02d}"
    destination_dir = upload_root() / relative_dir
    destination_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}.{extension}"
    destination = destination_dir / stored_name
    destination.write_bytes(content)

    preview_path = create_image_preview(content, extension, destination_dir, f"{destination.stem}_preview")
    return Document(
        user_id=user_id,
        original_name=original_name,
        stored_name=stored_name,
        file_path=str((relative_dir / stored_name).as_posix()),
        file_size=len(content),
        mime_type=mime_type,
        extension=extension,
        status=DocumentStatus.PENDING,
        direction=direction,
        preview_path=preview_path,
    )


async def get_user_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> Document | None:
    return await db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.is_deleted.is_(False),
        )
    )


def delete_document_file(document: Document) -> None:
    root = upload_root().resolve()
    file_path = (root / document.file_path).resolve()
    if file_path.is_relative_to(root) and file_path.exists():
        file_path.unlink()
    if document.preview_path:
        preview_path = (root / document.preview_path).resolve()
        if preview_path.is_relative_to(root) and preview_path.exists():
            preview_path.unlink()
