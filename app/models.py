from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import TIME, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Environment(Base):
    __tablename__ = 'environment'

    id = Column(UUID, primary_key=True)
    name = Column(String(250))
    description = Column(String(500))
    deleted = Column(SmallInteger)
    scan_start_time = Column(TIME(precision=6))
    scan_terminate_time = Column(TIME(precision=6))
    group_id = Column(UUID, nullable=False)
    created_by = Column(UUID)
    deleted_by = Column(UUID)
    active = Column(SmallInteger, nullable=False, server_default=text("0"))


class ResourceType(Base):
    __tablename__ = 'resource_type'

    id = Column(UUID, primary_key=True)
    code = Column(String(250))
    name = Column(String(250))


class Resource(Base):
    __tablename__ = 'resource'

    id = Column(UUID, primary_key=True)
    environment_id = Column(ForeignKey('environment.id'), nullable=False)
    resource_type_id = Column(ForeignKey('resource_type.id'), nullable=False)
    name = Column(String(250))
    ipv4 = Column(String(250))
    ipv6 = Column(String(250))
    console_username = Column(String(250))
    console_secret_id = Column(String(250))
    port = Column(Integer)
    protocol = Column(String(250))
    active = Column(SmallInteger, nullable=False, server_default=text("0"))
    
    environment = relationship('Environment')
    resource_type = relationship('ResourceType')