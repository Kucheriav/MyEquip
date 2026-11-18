from sqlalchemy import Column, Integer, Table, ForeignKey
from app.database import Base


CategoryParameterAssociation = Table(
    'category_parameter',
    Base.metadata,
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True),
    Column('parameter_id', Integer, ForeignKey('parameters.id'), primary_key=True)
)
