from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    last_name = Column(String)
    date_of_birth = Column(Date)
    email = Column(String, unique=True, index=True)  # FIXED: Changed from Email to String
    phone = Column(String, unique=True)
    pswd_hash = Column(String)
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