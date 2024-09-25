from sqlalchemy import Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# User Model
class User(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character: Mapped[str] = mapped_column(String, default="character1.svg")
    firstname: Mapped[str] = mapped_column(String, nullable=False)
    lastname: Mapped[str] = mapped_column(String, nullable=False)
    province: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    verified: Mapped[str] = mapped_column(String, default="false", nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    visited_places: Mapped[list["Visited"]] = relationship(
        "Visited", backref="user", lazy=True
    )
    liked_places: Mapped[list["Liked"]] = relationship(
        "Liked", backref="user", lazy=True
    )
    plans: Mapped[list["Plans"]] = relationship("Plans", backref="user", lazy=True)


# Visited Model
class Visited(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    fsq_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


# Liked Model
class Liked(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    fsq_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


# Plans Model
class Plans(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    fsq_id: Mapped[str] = mapped_column(String, nullable=False)
    place_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="upcoming", nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
