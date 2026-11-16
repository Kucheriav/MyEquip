from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    title = Column(String(100), nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)

    # Relationships
    club = relationship("Club", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="children")
    items = relationship("Item", back_populates="category")
    parameters = relationship(
        "Parameter",
        secondary="category_parameter",
        back_populates="categories"
    )