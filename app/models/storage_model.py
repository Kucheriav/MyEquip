from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Storage(Base):
    __tablename__ = "storages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)

    # Relationships
    club = relationship("Club", back_populates="storages")
    items = relationship("Item", back_populates="storage")