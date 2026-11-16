from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    storage_id = Column(Integer, ForeignKey('storages.id'), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(
        Enum('available', 'issued', 'maintenance', 'lost', name="item_status_enum"),
        default='available',
        nullable=False
    )
    serial_number = Column(String(100), unique=True, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="items")
    storage = relationship("Storage", back_populates="items")
    owner = relationship("User", back_populates="items")
    distributions = relationship("Distribution", back_populates="item")
    breakdowns = relationship("Breakdown", back_populates="item")
    parameters = relationship("ItemParameterValue", back_populates="item")