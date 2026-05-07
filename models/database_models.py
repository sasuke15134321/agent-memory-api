"""
Database Models for Creator Experiment Log
クリエイター実験ログ用データベースモデル
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Experiment(Base):
    __tablename__ = "experiments"

    # Primary key - unique experiment ID
    experiment_id = Column(String(36), primary_key=True, index=True)

    # Shop information (e.g., lost_fauna)
    shop = Column(String(100), nullable=False, index=True)

    # Platform (etsy/suzuri/pinterest/x)
    platform = Column(String(50), nullable=False, index=True)

    # Change type (title/description/tags/price/image)
    change_type = Column(String(50), nullable=False, index=True)

    # Before state (JSON format for flexibility)
    before = Column(JSON, nullable=False)

    # After state (JSON format for flexibility)
    after = Column(JSON, nullable=False)

    # Experiment date
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Record creation timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Experiment(id='{self.experiment_id}', shop='{self.shop}', platform='{self.platform}', change='{self.change_type}')>"

    def to_dict(self):
        """Convert experiment to dictionary"""
        return {
            "experiment_id": self.experiment_id,
            "shop": self.shop,
            "platform": self.platform,
            "change_type": self.change_type,
            "before": self.before,
            "after": self.after,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to experiments table
    experiment_id = Column(String(36), nullable=False, index=True)

    # Metric type (views/sales/clicks/followers)
    metric = Column(String(50), nullable=False, index=True)

    # Value before the experiment
    before_value = Column(Float, nullable=False)

    # Value after the experiment
    after_value = Column(Float, nullable=False)

    # Calculated improvement percentage
    improvement_percent = Column(Float, nullable=False)

    # Verdict (positive/negative/neutral)
    verdict = Column(String(20), nullable=False, index=True)

    # When the measurement was taken
    measurement_date = Column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self):
        return f"<ExperimentResult(experiment_id='{self.experiment_id}', metric='{self.metric}', verdict='{self.verdict}', improvement={self.improvement_percent}%)>"

    def to_dict(self):
        """Convert experiment result to dictionary"""
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric": self.metric,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "improvement_percent": self.improvement_percent,
            "verdict": self.verdict,
            "measurement_date": self.measurement_date.isoformat() if self.measurement_date else None
        }

# Additional helper model for experiment analytics
class ExperimentSummary(Base):
    __tablename__ = "experiment_summaries"

    id = Column(Integer, primary_key=True, index=True)
    shop = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    change_type = Column(String(50), nullable=False)
    total_experiments = Column(Integer, default=0)
    positive_results = Column(Integer, default=0)
    negative_results = Column(Integer, default=0)
    neutral_results = Column(Integer, default=0)
    average_improvement = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ExperimentSummary(shop='{self.shop}', platform='{self.platform}', success_rate={self.success_rate}%)>"