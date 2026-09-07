from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String, index=True, nullable=False)
    message_id = Column(Integer, index=True, nullable=False)
    text = Column(Text, nullable=True)
    datetime = Column(DateTime(timezone=True), nullable=True)
    media_type = Column(String, nullable=True)
    forwarded_from = Column(String, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    metrics = relationship("PostMetric", back_populates="post", cascade="all, delete-orphan")


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    views = Column(Integer, default=0)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    post = relationship("Post", back_populates="metrics")
