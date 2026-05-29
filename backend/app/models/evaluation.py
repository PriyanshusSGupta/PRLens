from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func
from app.db.base import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    prompt_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    precision = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    coverage = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
