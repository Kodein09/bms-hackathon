import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class NotificationType(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=20), default=NotificationType.INFO, nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="notifications")
