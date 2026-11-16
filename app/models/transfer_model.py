from sqlalchemy import Column, Integer, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    from_storage_id = Column(Integer, ForeignKey('storages.id'), nullable=False)
    to_storage_id = Column(Integer, ForeignKey('storages.id'), nullable=False)
    date = Column(Date, nullable=False)
    mover_id = Column(Integer, ForeignKey('users.id'), nullable=True)      # who sent the item
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=True)   # who accepted it
    comment = Column(Text)

    # Relationships
    item = relationship("Item", back_populates="transfers")
    from_storage = relationship("Storage", foreign_keys=[from_storage_id], back_populates="outgoing_transfers")
    to_storage = relationship("Storage", foreign_keys=[to_storage_id], back_populates="incoming_transfers")
    mover = relationship("User", foreign_keys=[mover_id], back_populates="transfers_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="transfers_received")
