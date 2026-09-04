import asyncio
import logging
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Post, PostMetric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_html_and_save(db: Session, html_content: str, channel: str) -> int:
    soup = BeautifulSoup(html_content, "html.parser")
    message_widgets = soup.find_all("div", class_="tgme_widget_message")
    
    added_count = 0
    for widget in message_widgets:
        raw_id = widget.get("data-post")
        if not raw_id or "/" not in raw_id:
            continue
            
        message_id = int(raw_id.split("/")[-1])
        
        # Текст поста
        text_el = widget.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text(separator="\n", strip=True) if text_el else ""
        
        # Перегляди
        views_el = widget.find("span", class_="tgme_widget_message_views")
        views = views_el.text.strip() if views_el else "0"

        # Шукаємо існуючий пост
        post = db.query(Post).filter(Post.channel == channel, Post.message_id == message_id).first()
        if not post:
            post = Post(channel=channel, message_id=message_id, text=text)
            db.add(post)
            db.flush()
            added_count += 1
        
        # Записуємо метрику
        metric = PostMetric(post_id=post.id, views=views)
        db.add(metric)

    db.commit()
    return added_count


async def fetch_channel_data(channel: str):
    url = f"https://t.me/s/{channel}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            db = SessionLocal()
            try:
                added = parse_html_and_save(db, response.text, channel)
                logger.info(f"[{channel}] Успішно оновлено. Нових постів: {added}")
            finally:
                db.close()
        else:
            logger.warning(f"[{channel}] Помилка завантаження: {response.status_code}")


async def run_scraper_loop():
    logger.info("Запуск фонового скрапера...")
    channels = [c.strip() for c in settings.CHANNELS.split(",") if c.strip()]
    
    while True:
        for channel in channels:
            try:
                await fetch_channel_data(channel)
            except Exception as e:
                logger.error(f"Помилка під час скрапінгу каналу {channel}: {e}")
        
        await asyncio.sleep(settings.FETCH_INTERVAL)