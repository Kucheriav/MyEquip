from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    storage_id = Column(Integer, ForeignKey('storages.id'))
