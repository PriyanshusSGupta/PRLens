from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db.base import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    attempts = Column(Integer, default=0)
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
