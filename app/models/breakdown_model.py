from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Breakdown(Base):
    __tablename__ = "breakdowns"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    comment = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    repaired_date = Column(Date, nullable=True)
    repairer_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    item = relationship("Item", back_populates="breakdowns")
    repairer = relationship("User", back_populates="breakdowns_repaired")