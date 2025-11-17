from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey
from app.database import Base


class Distribution(Base):
    __tablename__ = "distributions"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('users.id'))
    giver_id = Column(Integer, ForeignKey('users.id'))
    getter_id = Column(Integer, ForeignKey('users.id'))
    date = Column(Date)
    expiration_date = Column(Date)
    pswd_hash = Column(String)
    accepter_id = Column(Integer, ForeignKey('users.id'))
    accepting_date = Column(Date)
    comment = Column(Text)