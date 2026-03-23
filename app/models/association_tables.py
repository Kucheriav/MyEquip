from sqlalchemy import Column, Integer, Enum, Table, ForeignKey, String
from app.database import Base


UserInClubAssociation = Table(
    'user_in_club',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('club_id', Integer, ForeignKey('clubs.id'), primary_key=True),
    Column('privileges', Enum('getter', 'giver', 'owner', name="user_privileges_enum"),
           nullable=False, default='getter')
)

CategoryParameterAssociation = Table(
    'category_parameter',
    Base.metadata,
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True),
    Column('parameter_id', Integer, ForeignKey('parameters.id'), primary_key=True)
)