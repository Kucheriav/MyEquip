from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class ItemPhoto(Base):
    """A photo attached to an item.

    The file itself lives under DATA_DIR/uploads; the database keeps the
    path relative to that folder so the whole data directory can be moved
    or backed up as one unit.
    """

    __tablename__ = "item_photos"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(
        Integer,
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    item = relationship("Item", back_populates="photos")
