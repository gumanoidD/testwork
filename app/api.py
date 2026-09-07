import os
from typing import List, Optional
from datetime import datetime as dt_type, timedelta, timezone
import statistics
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, ConfigDict, Field

from app.database import SessionLocal, engine, Base
from app.models import Post, PostMetric

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Telegram Channel Parser API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Схемы ---
class MetricSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    views: int
    fetched_at: Optional[dt_type] = Field(default=None)

class PostSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    channel: str
    message_id: int
    text: Optional[str] = Field(default=None)
    datetime: Optional[dt_type] = Field(default=None)
    media_type: Optional[str] = Field(default=None)
    forwarded_from: Optional[str] = Field(default=None)
    fetched_at: Optional[dt_type] = Field(default=None)
    metrics: List[MetricSchema] = []

class TopPostSchema(PostSchema):
    score: float
    current_views: int

class ChannelStatSchema(BaseModel):
    channel: str
    total_posts: int
    last_fetched_at: Optional[dt_type] = None

# --- Healthcheck ---
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# --- UI ---
@app.get("/", response_class=HTMLResponse)
def read_index():
    possible_paths = ["index.html", "static/index.html", "app/static/index.html"]
    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path)
    return "<h3>API Online. Go to <a href='/docs'>/docs</a></h3>"

# --- Эндпоинты по ТЗ ---

@app.get("/channels", response_model=List[ChannelStatSchema])
def get_channels(db: Session = Depends(get_db)):
    """Список каналов с количеством постов и датой последнего сбора."""
    results = db.query(
        Post.channel,
        func.count(Post.id).label("total_posts"),
        func.max(Post.fetched_at).label("last_fetched_at")
    ).group_by(Post.channel).all()

    return [
        ChannelStatSchema(
            channel=r.channel,
            total_posts=r.total_posts,
            last_fetched_at=r.last_fetched_at
        ) for r in results
    ]

@app.get("/posts", response_model=List[PostSchema])
def get_posts(
    channel: Optional[str] = Query(None, description="Фильтр по каналу"),
    since: Optional[dt_type] = Query(None, description="Фильтр по дате (ISO format)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order: str = Query("date", pattern="^(date|views)$", description="Сортировка: date или views"),
    db: Session = Depends(get_db)
):
    """Список постов с фильтрацией, пагинацией и сортировкой."""
    query = db.query(Post).options(joinedload(Post.metrics))

    if channel:
        query = query.filter(Post.channel == channel)
    if since:
        query = query.filter(Post.datetime >= since)

    if order == "date":
        query = query.order_by(Post.datetime.desc())
    elif order == "views":
        # Сортировка по последним просмотрам
        subq = db.query(
            PostMetric.post_id,
            func.max(PostMetric.views).label("max_views")
        ).group_by(PostMetric.post_id).subquery()

        query = query.outerjoin(subq, Post.id == subq.c.post_id).order_by(desc(subq.c.max_views))

    return query.offset(offset).limit(limit).all()

@app.get("/channels/{name}/top", response_model=List[TopPostSchema])
def get_channel_top(
    name: str,
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Топ-посты за N дней относительно медианы канала."""
    cutoff = dt_type.now(timezone.utc) - timedelta(days=days)

    posts = db.query(Post).options(joinedload(Post.metrics)).filter(
        Post.channel == name,
        Post.datetime >= cutoff
    ).all()

    if not posts:
        return []

    # Собираем актуальные просмотры для каждого поста
    post_views_map = []
    for p in posts:
        latest_views = p.metrics[-1].views if p.metrics else 0
        post_views_map.append((p, latest_views))

    all_views = [v for _, v in post_views_map]
    if not all_views:
        return []

    med = statistics.median(all_views)
    if med == 0:
        med = 1.0  # Избегаем деления на 0

    result = []
    for p, v in post_views_map:
        score = round(v / med, 2)
        p_dict = PostSchema.model_validate(p).model_dump()
        p_dict["score"] = score
        p_dict["current_views"] = v
        result.append(p_dict)

    # Сортируем по score
    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:limit]
