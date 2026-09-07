import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Post, PostMetric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
PAUSE_BETWEEN_PAGES_SECONDS = 1


def parse_views(views_raw: str) -> int:
    """Конвертирует строковые просмотры ('1.5K', '2M', '500') в число int."""
    if not views_raw:
        return 0
    clean = views_raw.strip().upper().replace(" ", "").replace("\xa0", "")
    try:
        if "K" in clean:
            return int(float(clean.replace("K", "")) * 1_000)
        if "M" in clean:
            return int(float(clean.replace("M", "")) * 1_000_000)
        return int(clean)
    except ValueError:
        return 0


def parse_html_and_save(db: Session, html_content: str, channel: str) -> tuple[int, Optional[int]]:
    soup = BeautifulSoup(html_content, "html.parser")
    message_widgets = soup.find_all("div", class_="tgme_widget_message")

    if not message_widgets:
        return 0, None

    added_count = 0
    first_msg_id = None
    now_utc = datetime.now(timezone.utc)

    for widget in message_widgets:
        raw_id = widget.get("data-post")
        if not raw_id or "/" not in raw_id:
            continue

        message_id = int(raw_id.split("/")[-1])
        if first_msg_id is None:
            first_msg_id = message_id

        # Текст поста
        text_el = widget.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text(separator="\n", strip=True) if text_el else ""

        # Просмотры
        views_el = widget.find("span", class_="tgme_widget_message_views")
        views_raw = views_el.text.strip() if views_el else "0"
        views_count = parse_views(views_raw)

        # Парсинг даты
        time_el = widget.find("time")
        post_datetime = None
        if time_el and time_el.has_attr("datetime"):
            try:
                dt_str = time_el["datetime"].replace("Z", "+00:00")
                post_datetime = datetime.fromisoformat(dt_str)
            except ValueError:
                post_datetime = None

        # Страховка: если тега time нет или дата не распарсилась — берем текущую
        if not post_datetime:
            post_datetime = now_utc

        # Медиа
        media_type = None
        if widget.find("a", class_="tgme_widget_message_photo_wrap"):
            media_type = "photo"
        elif widget.find("video") or widget.find("a", class_="tgme_widget_message_video_player"):
            media_type = "video"
        elif widget.find("div", class_="tgme_widget_message_document"):
            media_type = "document"
        elif widget.find("a", class_="tgme_widget_message_voice_player"):
            media_type = "voice"

        # Репост
        fwd_el = widget.find("a", class_="tgme_widget_message_forwarded_from_name")
        forwarded_from = fwd_el.text.strip() if fwd_el else None

        # Сохранение / обновление поста
        post = db.query(Post).filter(Post.channel == channel, Post.message_id == message_id).first()
        if not post:
            post = Post(
                channel=channel,
                message_id=message_id,
                text=text,
                datetime=post_datetime,
                media_type=media_type,
                forwarded_from=forwarded_from,
                fetched_at=now_utc
            )
            db.add(post)
            db.flush()
            added_count += 1
        else:
            if not post.datetime:
                post.datetime = post_datetime
            if media_type:
                post.media_type = media_type
            if forwarded_from:
                post.forwarded_from = forwarded_from

        # Добавление метрики
        metric = PostMetric(
            post_id=post.id,
            views=views_count,
            fetched_at=now_utc
        )
        db.add(metric)

    db.commit()
    return added_count, first_msg_id


async def _fetch_page_with_retries(client: httpx.AsyncClient, url: str, channel: str) -> Optional[httpx.Response]:
    """Делает GET с несколькими попытками и backoff. Возвращает None, если все попытки не удались."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                return resp
            logger.warning(f"[{channel}] попытка {attempt}/{MAX_RETRIES}: HTTP {resp.status_code} на {url}")
        except httpx.HTTPError as e:
            logger.warning(f"[{channel}] попытка {attempt}/{MAX_RETRIES}: сетевая ошибка ({e}) на {url}")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)

    logger.error(f"[{channel}] не удалось получить {url} после {MAX_RETRIES} попыток")
    return None


async def fetch_channel_data(channel: str, backfill: bool = False, max_pages: int = 5):
    url = f"https://t.me/s/{channel}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        current_url = url
        pages_scraped = 0
        total_added = 0

        while current_url and pages_scraped < (max_pages if backfill else 1):
            resp = await _fetch_page_with_retries(client, current_url, channel)
            if resp is None:
                # Все попытки исчерпаны для этой страницы — прекращаем сбор
                # по каналу, но не роняем весь процесс.
                break

            db = SessionLocal()
            try:
                added, first_id = parse_html_and_save(db, resp.text, channel)
                total_added += added
                pages_scraped += 1

                if backfill and first_id:
                    current_url = f"https://t.me/s/{channel}?before={first_id}"
                    if pages_scraped < max_pages:
                        await asyncio.sleep(PAUSE_BETWEEN_PAGES_SECONDS)
                else:
                    break
            finally:
                db.close()

        logger.info(f"[{channel}] Сбор завершен. Страниц: {pages_scraped}, новых постов: {total_added}")


def fetch_channel(db: Session, channel: str, backfill: bool = False):
    """Синхронный запуск для CLI"""
    asyncio.run(fetch_channel_data(channel, backfill=backfill))


async def run_scraper_loop():
    logger.info("Запуск фонового скрапера...")
    channels = [c.strip() for c in settings.CHANNELS.split(",") if c.strip()]

    while True:
        for channel in channels:
            try:
                await fetch_channel_data(channel, backfill=False)
            except Exception as e:
                logger.error(f"Ошибка скрапинга канала {channel}: {e}")

        await asyncio.sleep(settings.FETCH_INTERVAL)
