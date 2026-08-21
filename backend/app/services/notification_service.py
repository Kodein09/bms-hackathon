from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


async def get_user_notifications(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    only_unread: bool = False,
) -> tuple[list[Notification], int]:
    filters = [Notification.user_id == user_id]
    if only_unread:
        filters.append(Notification.is_read.is_(False))

    notifications_result = await db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(skip)
        .limit(limit)
    )
    unread_count = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return list(notifications_result), int(unread_count or 0)


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: NotificationType,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_as_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> Notification | None:
    notification = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if notification is None:
        return None
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_as_read(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount or 0


async def delete_notification(db: AsyncSession, notification_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        delete(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    await db.commit()
    return bool(result.rowcount)
