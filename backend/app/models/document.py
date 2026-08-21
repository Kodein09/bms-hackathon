import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class DocumentDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(150))
    extension: Mapped[str] = mapped_column(String(20))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20), default=DocumentStatus.PENDING, nullable=False
    )
    direction: Mapped[DocumentDirection] = mapped_column(
        Enum(DocumentDirection, native_enum=False, length=20), default=DocumentDirection.OUTGOING, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    preview_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="documents")
