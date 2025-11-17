from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    title = Column(String)
    club_id = Column(Integer, ForeignKey('clubs.id'))
    parent = relationship("Category", remote_side=[id])
    parameters = relationship("Parameter", back_populates="category")