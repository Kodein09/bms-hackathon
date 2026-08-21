from pydantic import BaseModel

from app.schemas.user import UserCreate, UserRead, UserResponse, UserUpdate


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


from app.schemas.notification import (  # noqa: E402
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationTypeValue,
    NotificationUpdate,
)
from app.schemas.document import (
    DocumentDirectionValue,
    DocumentResponse,
    DocumentStatusUpdate,
    DocumentStatusValue,
    DocumentUploadResult,
)

__all__ = [
    "NotificationCreate",
    "NotificationListResponse",
    "NotificationResponse",
    "NotificationTypeValue",
    "NotificationUpdate",
    "DocumentDirectionValue",
    "DocumentResponse",
    "DocumentStatusUpdate",
    "DocumentStatusValue",
    "DocumentUploadResult",
    "RefreshRequest",
    "Token",
    "UserCreate",
    "UserRead",
    "UserResponse",
    "UserUpdate",
]
