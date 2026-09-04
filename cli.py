import argparse
import asyncio
import httpx
from bs4 import BeautifulSoup
from app.config import settings
from app.database import SessionLocal, engine, Base
from app.scraper import parse_html_and_save

async def collect_channel(channel: str, backfill: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    url = f"https://t.me/s/{channel}"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                added = parse_html_and_save(db, resp.text, channel)
                print(f"[{channel}] Успішно зібрано. Нових постів: {added}")
                
                # Приклад базового backfill через пагінацію (before)
                if backfill:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    messages = soup.find_all("div", class_="tgme_widget_message")
                    if messages:
                        first_post_id = messages[0].get("data-post", "").split("/")[-1]
                        if first_post_id:
                            backfill_url = f"https://t.me/s/{channel}?before={first_post_id}"
                            bf_resp = await client.get(backfill_url, headers={"User-Agent": "Mozilla/5.0"})
                            if bf_resp.status_code == 200:
                                bf_added = parse_html_and_save(db, bf_resp.text, channel)
                                print(f"[{channel}] Backfill виконано. Додано з історії: {bf_added}")
            else:
                print(f"[{channel}] Помилка запиту: {resp.status_code}")
    finally:
        db.close()

async def main():
    parser = argparse.ArgumentParser(description="CLI Скрапер Telegram-каналів")
    parser.add_argument("command", choices=["collect"], help="Команда для збору даних")
    parser.add_argument("--backfill", action="store_true", help="Глибокий збір історії")
    args = parser.parse_args()

    if args.command == "collect":
        channels = [c.strip() for c in settings.CHANNELS.split(",") if c.strip()]
        for channel in channels:
            await collect_channel(channel, backfill=args.backfill)

if __name__ == "__main__":
    asyncio.run(main())