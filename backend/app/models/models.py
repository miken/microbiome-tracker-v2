"""
SQLAlchemy models
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date,
    ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    pin_hash = Column(String(256), nullable=False)
    gender = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    entries = relationship("Entry", back_populates="user")


class Week(Base):
    __tablename__ = "weeks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, unique=True, nullable=False)  # Sunday
    end_date = Column(Date, nullable=False)  # Saturday
    is_active = Column(Boolean, default=True)

    entries = relationship("Entry", back_populates="week")


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_id = Column(Integer, ForeignKey("weeks.id"), nullable=False)
    item_name = Column(String(200), nullable=False)  # Original input
    item_name_normalized = Column(String(200), nullable=False)  # Lowercase, singularized
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="entries")
    week = relationship("Week", back_populates="entries")

    __table_args__ = (
        UniqueConstraint("user_id", "week_id", "item_name_normalized", name="uq_user_week_item"),
        Index("ix_entry_user_week", "user_id", "week_id"),
    )


class VeggieBenefitsCache(Base):
    __tablename__ = "veggie_benefits_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_name_normalized = Column(String(200), unique=True, nullable=False)
    benefits_html = Column(Text, nullable=True)
    fun_fact = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
