from sqlalchemy import Column, Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ClubMember(Base):
    """Membership of a user in a club with a per-club role.

    A user can be a tourist in one club and a leader or storekeeper in
    another. Staff access (leader/storekeeper) is derived from these
    rows, not from a single global flag.
    """
    __tablename__ = "club_members"
    __table_args__ = (
        UniqueConstraint("user_id", "club_id", name="uq_club_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False, index=True)
    role = Column(
        Enum("leader", "storekeeper", "tourist", name="club_member_role_enum"),
        nullable=False,
        default="tourist",
    )

    user = relationship("User", back_populates="memberships")
    club = relationship("Club", back_populates="members")
