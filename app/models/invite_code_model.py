from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # None = bootstrap code
    created_at = Column(DateTime, nullable=False)
    used_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    used_at = Column(DateTime, nullable=True)

    creator = relationship("User", foreign_keys=[created_by], back_populates="invites_created")
    used_by_user = relationship("User", foreign_keys=[used_by], back_populates="invite_used")
