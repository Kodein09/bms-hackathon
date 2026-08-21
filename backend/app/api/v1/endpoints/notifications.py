from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.core.websocket import notification_manager
from app.db.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationTypeValue,
)
from app.services.notification_service import (
    create_notification,
    delete_notification,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])
ws_router = APIRouter()


def to_payload(notification: Notification) -> dict:
    return NotificationResponse.model_validate(notification).model_dump(mode="json")


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    notifications, unread_count = await get_user_notifications(
        db, current_user.id, skip=skip, limit=limit, only_unread=unread_only
    )
    return NotificationListResponse(items=notifications, unread_count=unread_count)


@router.get("/unread-count")
async def unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    _, count = await get_user_notifications(db, current_user.id, skip=0, limit=1)
    return {"unread_count": count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Notification:
    notification = await mark_as_read(db, notification_id, current_user.id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.put("/read-all")
async def read_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    return {"updated_count": await mark_all_as_read(db, current_user.id)}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await delete_notification(db, notification_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_system_notification(
    notification_data: NotificationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Notification:
    del current_user  # Admin role is not part of the current User model yet.
    notification = await create_notification(
        db,
        notification_data.user_id,
        notification_data.title,
        notification_data.message,
        NotificationType(notification_data.type.value),
    )
    await notification_manager.send_to_user(notification.user_id, to_payload(notification))
    return notification


@ws_router.websocket("/ws/notifications/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: UUID) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Access token required")
        return

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access" or UUID(payload["sub"]) != user_id:
            raise ValueError
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=1008, reason="Invalid access token")
        return

    await notification_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)
    except Exception:
        notification_manager.disconnect(user_id, websocket)
        await websocket.close(code=1011)
