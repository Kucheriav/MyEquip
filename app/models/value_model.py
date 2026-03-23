from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Value(Base):
    __tablename__ = "values"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String, nullable=False)
    parameter_id = Column(Integer, ForeignKey('parameters.id'), nullable=False)

    # Relationships
    parameter = relationship("Parameter", back_populates="values")