import argparse
import asyncio
import logging
from app.config import settings
from app.scraper import fetch_channel_data

logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="CLI Скрапер Telegram-каналов")
    parser.add_argument("command", choices=["collect"], help="Команда для сбора данных")
    parser.add_argument("--backfill", action="store_true", help="Глубокий сбор истории")
    args = parser.parse_args()

    if args.command == "collect":
        channels = [c.strip() for c in settings.CHANNELS.split(",") if c.strip()]
        if not channels:
            logger.warning("Список каналов пуст — проверь CHANNELS в .env")
            return

        for channel in channels:
            try:
                await fetch_channel_data(channel, backfill=args.backfill)
            except Exception as e:
                logger.error(f"[{channel}] Не удалось собрать канал: {e}")


if __name__ == "__main__":
    asyncio.run(main())
