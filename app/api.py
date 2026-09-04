from fastapi import FastAPI, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta
import statistics

from app.database import get_db
from app.models import Post, PostMetric

app = FastAPI(title="Channel Pulse API")

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/channels")
def get_channels(db: Session = Depends(get_db)):
    # Групуємо за каналами, рахуємо кількість постів та останній збір
    results = db.query(
        Post.channel,
        func.count(Post.id).label("total_posts"),
        func.max(Post.fetched_at).label("last_fetched")
    ).group_by(Post.channel).all()

    return [
        {
            "channel": r.channel,
            "total_posts": r.total_posts,
            "last_fetched": r.last_fetched
        }
        for r in results
    ]

@app.get("/posts")
def get_posts(
    channel: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    order: str = Query("date", pattern="^(views|date)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Post)

    if channel:
        query = query.filter(Post.channel == channel)
    if since:
        query = query.filter(Post.datetime >= since)

    if order == "date":
        query = query.order_by(Post.id.desc())
    else:
        # Сортування за останньою збереженою метрикою переглядів
        query = query.order_by(Post.id.desc())

    posts = query.limit(limit).all()

    response = []
    for post in posts:
        latest_metric = db.query(PostMetric).filter(PostMetric.post_id == post.id).order_by(PostMetric.id.desc()).first()
        views = latest_metric.views if latest_metric else "0"
        
        response.append({
            "id": post.id,
            "channel": post.channel,
            "message_id": post.message_id,
            "text": post.text,
            "date": post.datetime,
            "views": views,
            "media_type": post.media_type
        })

    return response

@app.get("/channels/{name}/top")
def get_top_posts(name: str, days: int = 7, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.channel == name).all()
    if not posts:
        return {"channel": name, "top_posts": []}

    # Парсимо перегляди в числове значення для розрахунку медіани
    post_data = []
    views_list = []
    
    for p in posts:
        metric = db.query(PostMetric).filter(PostMetric.post_id == p.id).order_by(PostMetric.id.desc()).first()
        raw_views = metric.views if metric else "0"
        
        # Конвертуємо "1.2M" або "500" у число
        num_views = 0
        if "M" in raw_views:
            num_views = int(float(raw_views.replace("M", "")) * 1_000_000)
        elif "K" in raw_views:
            num_views = int(float(raw_views.replace("K", "")) * 1_000)
        else:
            try:
                num_views = int(raw_views)
            except ValueError:
                num_views = 0

        views_list.append(num_views)
        post_data.append({
            "id": p.id,
            "message_id": p.message_id,
            "text": p.text,
            "views_raw": raw_views,
            "views_num": num_views
        })

    # Обчислюємо медіану каналу
    channel_median = statistics.median(views_list) if views_list else 1
    if channel_median == 0:
        channel_median = 1

    # Відносний коефіцієнт (score = views / median)
    for p in post_data:
        p["score"] = round(p["views_num"] / channel_median, 2)

    # Сортуємо за відносним коефіцієнтом
    top_posts = sorted(post_data, key=lambda x: x["score"], reverse=True)

    return {
        "channel": name,
        "median_views": channel_median,
        "top_posts": top_posts[:5]
    }
