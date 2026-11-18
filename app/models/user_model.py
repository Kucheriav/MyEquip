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
    email = Column(String(120), unique=True, index=True)
    phone = Column(String(20), unique=True)
    pswd_hash = Column(String(128))
    status = Column(Enum('guest', 'unverified', 'full', name="user_status_enum"),
                    nullable=False, default='guest')
    # Summary role for the GUI / quick checks. The source of truth for
    # club access is the club_members table (a user may be, for example,
    # a tourist in one club and a storekeeper in another).
    role = Column(Enum('leader', 'storekeeper', 'tourist', name="user_role_enum"),
                  nullable=False, default='tourist')

    # Relationships
    memberships = relationship(
        "ClubMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
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

    @property
    def club_ids(self):
        return [m.club_id for m in self.memberships]
