from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    groups = relationship("HotelGroup", back_populates="owner")


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String)
    state = Column(String)
    keys = Column(Integer)
    kind = Column(String)
    brand = Column(String)
    parent = Column(String)
    website = Column(String)
    booking_name = Column(String)
    expedia_name = Column(String)
    tripadvisor_name = Column(String)

    snapshots = relationship("ReviewSnapshot", back_populates="hotel", order_by="ReviewSnapshot.collected_at.desc()", cascade="all, delete-orphan")
    group_memberships = relationship("HotelGroupMembership", back_populates="hotel")


class ReviewSnapshot(Base):
    __tablename__ = "review_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source = Column(String, nullable=False)  # "csv_import" | "live"

    google_score = Column(Float, nullable=True)
    google_count = Column(Integer, nullable=True)
    booking_score = Column(Float, nullable=True)
    booking_count = Column(Integer, nullable=True)
    expedia_score = Column(Float, nullable=True)
    expedia_count = Column(Integer, nullable=True)
    tripadvisor_score = Column(Float, nullable=True)
    tripadvisor_count = Column(Integer, nullable=True)

    google_normalized = Column(Float, nullable=True)
    booking_normalized = Column(Float, nullable=True)
    expedia_normalized = Column(Float, nullable=True)
    tripadvisor_normalized = Column(Float, nullable=True)
    weighted_average = Column(Float, nullable=True)

    hotel = relationship("Hotel", back_populates="snapshots")


class HotelGroup(Base):
    __tablename__ = "hotel_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="groups")
    memberships = relationship("HotelGroupMembership", back_populates="group", cascade="all, delete-orphan")


class HotelGroupMembership(Base):
    __tablename__ = "hotel_group_memberships"

    group_id = Column(Integer, ForeignKey("hotel_groups.id"), primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), primary_key=True)

    group = relationship("HotelGroup", back_populates="memberships")
    hotel = relationship("Hotel", back_populates="group_memberships")

    __table_args__ = (UniqueConstraint("group_id", "hotel_id"),)
