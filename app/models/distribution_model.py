from sqlalchemy import Column, Integer, Date, Text, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Distribution(Base):
    __tablename__ = "distributions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    giver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    getter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    accepter_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    accepting_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)
    distribution_date = Column(Date, nullable=False)
    status = Column(
        Enum('issued', 'returned', 'lost', 'extended', name="distribution_status_enum"),
        default='issued',
        nullable=False
    )
    comment = Column(Text)

    __table_args__ = (
        Index('ix_dist_item', 'item_id'),
        Index('ix_dist_giver', 'giver_id'),
        Index('ix_dist_getter', 'getter_id'),
        Index('ix_dist_status', 'status'),
        Index('ix_dist_exp_date', 'expiration_date'),
    )

    # Relationships
    item = relationship("Item", back_populates="distributions")
    giver = relationship("User", foreign_keys=[giver_id], back_populates="distributions_given")
    getter = relationship("User", foreign_keys=[getter_id], back_populates="distributions_received")
    accepter = relationship("User", foreign_keys=[accepter_id], back_populates="distributions_accepted")