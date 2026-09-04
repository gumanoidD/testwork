import asyncio
import uvicorn
from app.api import app
from app.database import engine, Base
from app.scraper import run_scraper_loop

async def main():
    # Автоматично створюємо таблиці в БД, якщо їх ще немає
    Base.metadata.create_all(bind=engine)

    # Запускаємо фоновий скрапер
    asyncio.create_task(run_scraper_loop())
    
    # Запускаємо сервер
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())