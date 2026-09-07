from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Post, PostMetric
from app.scraper import parse_html_and_save, parse_views

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    # StaticPool держит одно и то же соединение на все потоки — без этого
    # TestClient (который выполняет запрос в отдельном потоке через anyio)
    # видит уже другую, пустую in-memory базу ("no such table").
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_parse_html_fixture_and_idempotency(db_session):
    fixture_path = Path(__file__).parent / "fixtures" / "channel_preview.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    # 1. Первый проход
    added, _ = parse_html_and_save(db_session, html_content, "durov")
    assert added == 2
    assert db_session.query(Post).count() == 2
    assert db_session.query(PostMetric).count() == 2

    # 2. Повторный проход (идемпотентность)
    added_again, _ = parse_html_and_save(db_session, html_content, "durov")
    assert added_again == 0  # новые посты не создаются
    assert db_session.query(Post).count() == 2
    assert db_session.query(PostMetric).count() == 4  # метрики продолжают копиться


def test_views_parsing():
    assert parse_views("100") == 100
    assert parse_views("1.5K") == 1500
    assert parse_views("2.5M") == 2500000
    assert parse_views("") == 0


def test_analytics_median_math():
    """Сама формула медианы/score — быстрая проверка арифметики без БД и HTTP."""
    import statistics

    views_list = [1000, 2000, 3000, 4000, 10000]  # медиана = 3000
    median_val = statistics.median(views_list)
    assert median_val == 3000

    post_views = 6000
    score = round(post_views / median_val, 2)
    assert score == 2.0


def test_channel_top_endpoint(db_session, monkeypatch):
    """Реальный вызов /channels/{name}/top через TestClient — проверяем,
    что ручка действительно считает score по медиане, а не только формула сама по себе."""
    from app import api as api_module

    # Подменяем зависимость get_db на тестовую in-memory сессию
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    api_module.app.dependency_overrides[api_module.get_db] = override_get_db
    client = TestClient(api_module.app)

    now = datetime.now(timezone.utc)

    def make_post(message_id: int, views: int, days_ago: int = 1):
        post = Post(
            channel="durov",
            message_id=message_id,
            text=f"post {message_id}",
            datetime=now - timedelta(days=days_ago),
            fetched_at=now,
        )
        db_session.add(post)
        db_session.flush()
        db_session.add(PostMetric(post_id=post.id, views=views, fetched_at=now))
        db_session.commit()

    # Медиана views = 3000 (посты: 1000, 2000, 3000, 4000, 10000)
    make_post(1, 1000)
    make_post(2, 2000)
    make_post(3, 3000)
    make_post(4, 4000)
    make_post(5, 10000)

    response = client.get("/channels/durov/top", params={"days": 7})
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 5
    # Топ пост — 10000 просмотров, score = 10000 / 3000 ≈ 3.33
    assert data[0]["current_views"] == 10000
    assert data[0]["score"] == pytest.approx(3.33, abs=0.01)
    # Порядок по убыванию score
    scores = [item["score"] for item in data]
    assert scores == sorted(scores, reverse=True)

    api_module.app.dependency_overrides.clear()
