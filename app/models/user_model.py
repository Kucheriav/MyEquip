from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    email = Column(String(120), unique=True, index=True)  # FIXED: Changed from Email to String
    phone = Column(String(20), unique=True)
    pswd_hash = Column(String(128))
    status = Column(Enum('guest', 'unverified', 'full', name="user_status_enum"),
                    nullable=False, default='guest')

    # Relationships
    clubs = relationship(
        "Club",
        secondary="user_in_club",
        back_populates="users"
    )
    items = relationship("Item", back_populates="owner")
    distributions_given = relationship(
        "Distribution",
        foreign_keys="Distribution.giver_id",
        back_populates="giver"
    )
    distributions_received = relationship(
        "Distribution",
        foreign_keys="Distribution.getter_id",
        back_populates="getter"
    )
    distributions_accepted = relationship(
        "Distribution",
        foreign_keys="Distribution.accepter_id",
        back_populates="accepter"
    )
    breakdowns_repaired = relationship("Breakdown", back_populates="repairer")
    transfers_sent = relationship("Transfer", foreign_keys="Transfer.mover_id", back_populates="mover")
    transfers_received = relationship("Transfer", foreign_keys="Transfer.receiver_id", back_populates="receiver")
    invites_created = relationship("InviteCode", foreign_keys="InviteCode.created_by", back_populates="creator")
    invite_used = relationship("InviteCode", foreign_keys="InviteCode.used_by", back_populates="used_by_user")