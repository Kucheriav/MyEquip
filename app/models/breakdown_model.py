from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.database import Base


class Breakdown(Base):
    __tablename__ = "breakdowns"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer,  ForeignKey('items.id'))
    comment = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    repaired_date = Column(Date)
    repairer_id = Column(Integer, ForeignKey('users.id'))
