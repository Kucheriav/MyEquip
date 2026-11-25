from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ItemPhotoResponse(BaseModel):
    """What the client sees about a photo.

    The on-disk path is deliberately not exposed: images are served through
    an access-checked endpoint, not by guessing file names.
    """

    id: int
    item_id: int
    original_name: Optional[str] = None
    content_type: str
    size: int
    uploaded_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
