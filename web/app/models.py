from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.sql import expression
from .database import Base


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, server_default=expression.true(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Webhook(Base):
    __tablename__ = 'webhooks'
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False)
    event = Column(String(128), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())