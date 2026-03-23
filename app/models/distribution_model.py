from sqlalchemy import Column, Integer, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class Distribution(Base):
    __tablename__ = "distributions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)  # FIXED: was users.id
    giver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    getter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=True)
    accepter_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    accepting_date = Column(Date, nullable=True)
    status = Column(
        Enum('issued', 'returned', 'lost', 'extended', name="distribution_status_enum"),
        default='issued',
        nullable=False
    )
    comment = Column(Text)

    # Relationships
    item = relationship("Item", back_populates="distributions")
    giver = relationship("User", foreign_keys=[giver_id], back_populates="distributions_given")
    getter = relationship("User", foreign_keys=[getter_id], back_populates="distributions_received")
    accepter = relationship("User", foreign_keys=[accepter_id], back_populates="distributions_accepted")