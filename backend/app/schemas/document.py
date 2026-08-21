import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class DocumentStatusValue(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class DocumentDirectionValue(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatusValue


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    original_name: str
    stored_name: str
    file_path: str
    file_size: int
    mime_type: str
    extension: str
    status: DocumentStatusValue
    direction: DocumentDirectionValue
    is_deleted: bool
    preview_path: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResult(BaseModel):
    filename: str
    success: bool
    document: DocumentResponse | None = None
    error: str | None = None
