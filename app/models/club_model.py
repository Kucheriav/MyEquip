from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    # Relationships
    members = relationship(
        "ClubMember",
        back_populates="club",
        cascade="all, delete-orphan",
    )
    categories = relationship("Category", back_populates="club")
    storages = relationship("Storage", back_populates="club")
    items = relationship("Item", back_populates="club")
