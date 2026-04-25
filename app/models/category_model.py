from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    title = Column(String, nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)

    __table_args__ = (
        Index('ix_category_club', 'club_id'),
        Index('ix_category_parent', 'parent_id'),
    )

    club = relationship("Club", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="children")
    items = relationship("Item", back_populates="category")
    parameters = relationship(
        "Parameter",
        secondary="category_parameter",
        back_populates="categories"
    )