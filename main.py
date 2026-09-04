import typer
from app.database import engine, Base, SessionLocal
from app.config import settings
from app.scraper import fetch_channel

# Автоматично створюємо таблиці (posts та post_metrics), якщо їх немає
Base.metadata.create_all(bind=engine)

app = typer.Typer(help="Channel Pulse CLI")

@app.callback()
def main():
    """Channel Pulse CLI Manager"""
    pass

@app.command()
def collect(
    channel: str = typer.Option(None, "--channel", "-c", help="Конкретний канал для збору"),
    backfill: bool = typer.Option(False, "--backfill", help="Глибокий прохід по історії")
):
    """Збір постів з каналів"""
    db = SessionLocal()
    try:
        channels_to_scrape = [channel] if channel else settings.CHANNELS
        for ch in channels_to_scrape:
            fetch_channel(db, ch, backfill=backfill)
    finally:
        db.close()

if __name__ == "__main__":
    app()