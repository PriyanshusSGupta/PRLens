from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ReviewRun(Base):
    __tablename__ = "review_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    findings_count = Column(Integer, default=0)

    pull_request = relationship("PullRequest", back_populates="review_runs")
