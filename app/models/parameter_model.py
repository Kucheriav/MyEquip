from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class Parameter(Base):
    __tablename__ = "parameters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    param_type = Column(
        Enum('int', 'bool', 'str', 'float', name="param_type_enum"),
        nullable=False,
        default='str'
    )

    # Relationships
    values = relationship("Value", back_populates="parameter", cascade="all, delete-orphan")
    categories = relationship(
        "Category",
        secondary="category_parameter",
        back_populates="parameters"
    )
    # delete-orphan: removing a parameter removes its per-item values
    # (parameter_id is NOT NULL)
    item_values = relationship(
        "ItemParameterValue",
        back_populates="parameter",
        cascade="all, delete-orphan",
    )