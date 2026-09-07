import asyncio
import uvicorn
from app.api import app
from app.scraper import run_scraper_loop

async def main():
    asyncio.create_task(run_scraper_loop())
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
