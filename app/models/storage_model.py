from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base



class Storage(Base):
    __tablename__ = "storages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(String)
    club_id = Column(Integer, ForeignKey('clubs.id'))
