from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel: Mapped[str] = mapped_column(String, index=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    datetime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(String)
    media_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    forwarded_from: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    metrics: Mapped[List["PostMetric"]] = relationship("PostMetric", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("channel", "message_id", name="uix_channel_message"),
    )

class PostMetric(Base):
    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    views: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    post: Mapped["Post"] = relationship("Post", back_populates="metrics")