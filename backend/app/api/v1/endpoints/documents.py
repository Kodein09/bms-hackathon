from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.document_service import DocumentValidationError
from app.core.security import get_current_user
from app.core.websocket import notification_manager
from app.db.database import get_db
from app.models.document import Document, DocumentDirection, DocumentStatus
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.document import (
    DocumentDirectionValue,
    DocumentResponse,
    DocumentStatusUpdate,
    DocumentUploadResult,
)
from app.services.document_service import (
    delete_document_file,
    get_user_document,
    save_upload,
)
from app.services.notification_service import create_notification


router = APIRouter(prefix="/documents", tags=["documents"])


def upload_error_message(error: Exception) -> str:
    if isinstance(error, DocumentValidationError):
        return str(error)
    return "Не удалось сохранить файл"


async def notify_user(user_id: UUID, title: str, message: str, notification_type: NotificationType, db: AsyncSession) -> None:
    notification = await create_notification(db, user_id, title, message, notification_type)
    await notification_manager.send_to_user(
        user_id,
        {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.type.value,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        },
    )


@router.post("/upload", response_model=list[DocumentUploadResult])
async def upload_documents(
    files: Annotated[list[UploadFile], File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    direction: DocumentDirectionValue = Query(default=DocumentDirectionValue.OUTGOING),
) -> list[DocumentUploadResult]:
    results: list[DocumentUploadResult] = []
    user_id = current_user.id
    document_direction = DocumentDirection(direction.value)
    for upload in files:
        try:
            document = await save_upload(upload, user_id, document_direction)
            db.add(document)
            await db.commit()
            await db.refresh(document)
            await notify_user(
                user_id,
                "Файл загружен",
                f"Файл «{document.original_name}» успешно загружен.",
                NotificationType.SUCCESS,
                db,
            )
            results.append(DocumentUploadResult(filename=upload.filename or "unnamed", success=True, document=document))
        except Exception as exc:
            await db.rollback()
            results.append(DocumentUploadResult(filename=upload.filename or "unnamed", success=False, error=upload_error_message(exc)))
    return results


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    direction: DocumentDirection | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["created_at", "file_size"] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
) -> list[Document]:
    filters = [Document.user_id == current_user.id, Document.is_deleted.is_(False)]
    if document_status:
        filters.append(Document.status == document_status)
    if direction:
        filters.append(Document.direction == direction)
    if date_from:
        filters.append(Document.created_at >= date_from)
    if date_to:
        filters.append(Document.created_at <= date_to)
    sort_column = Document.created_at if sort_by == "created_at" else Document.file_size
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    result = await db.scalars(
        select(Document).where(*filters).order_by(ordering).offset(skip).limit(limit)
    )
    return list(result)


@router.get("/{document_id}/info", response_model=DocumentResponse)
async def document_info(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    document = await get_user_document(db, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return document


@router.get("/{document_id}")
async def download_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    document = await get_user_document(db, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    file_path = (Path(settings.upload_dir) / document.file_path).resolve()
    upload_root = Path(settings.upload_dir).resolve()
    if not file_path.is_relative_to(upload_root) or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден на диске")
    return FileResponse(file_path, media_type=document.mime_type, filename=document.original_name)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    document = await get_user_document(db, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    document.is_deleted = True
    await db.commit()


@router.put("/{document_id}/status", response_model=DocumentResponse)
async def update_document_status(
    document_id: UUID,
    status_data: DocumentStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    document = await get_user_document(db, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    document.status = DocumentStatus(status_data.status.value)
    await db.commit()
    await db.refresh(document)
    await notify_user(
        current_user.id,
        "Статус документа изменён",
        f"Статус файла «{document.original_name}»: {document.status.value}.",
        NotificationType.INFO,
        db,
    )
    return document
