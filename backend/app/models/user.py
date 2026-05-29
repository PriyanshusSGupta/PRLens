from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    auth_provider = Column(String, nullable=False, default="email")
    github_id = Column(Integer, unique=True, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    username = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    tokens = relationship("UserToken", back_populates="user")
