from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    storage_id = Column(Integer, ForeignKey('storages.id'), nullable=False)
    # Ownership is by club and never changes (a transfer only moves the
    # item between storages of the same club).
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False, index=True)
    status = Column(
        Enum('available', 'issued', 'maintenance', 'lost', name="item_status_enum"),
        default='available',
        nullable=False
    )
    serial_number = Column(String(100), unique=True, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="items")
    storage = relationship("Storage", back_populates="items")
    club = relationship("Club", back_populates="items")
    distributions = relationship("Distribution", back_populates="item")
    breakdowns = relationship("Breakdown", back_populates="item")
    transfers = relationship("Transfer", back_populates="item")
    # delete-orphan: removing an item removes its parameter values,
    # not NULL-updates them (item_id is NOT NULL)
    parameters = relationship(
        "ItemParameterValue",
        back_populates="item",
        cascade="all, delete-orphan",
    )
