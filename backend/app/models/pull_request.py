from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    state = Column(String, nullable=False, default="open")
    author = Column(String, nullable=False)
    base_sha = Column(String, nullable=False)
    head_sha = Column(String, nullable=False)
    url = Column(String, nullable=True)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    repository = relationship("Repository", back_populates="pull_requests")
    findings = relationship("Finding", back_populates="pull_request")
    review_runs = relationship("ReviewRun", back_populates="pull_request")
