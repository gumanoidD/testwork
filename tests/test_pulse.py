import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Post, PostMetric
from app.scraper import parse_html_and_save

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_parser_with_fixture(db_session):
    fixture_path = Path(__file__).parent / "fixtures" / "channel_preview.html"
    html_content = fixture_path.read_text(encoding="utf-8")
    
    # Перший прохід
    added = parse_html_and_save(db_session, html_content, "durov")
    assert added == 2
    assert db_session.query(Post).count() == 2
    assert db_session.query(PostMetric).count() == 2

    # Перевірка ідемпотентності (повторний прохід не створює нові дублі постів)
    added_again = parse_html_and_save(db_session, html_content, "durov")
    assert added_again == 0
    assert db_session.query(Post).count() == 2
    assert db_session.query(PostMetric).count() == 4  # Метрики зберігають динаміку

def test_analytics_median_score():
    views_list = [100, 200, 300, 400, 500]
    views_list.sort()
    median = views_list[len(views_list) // 2]
    
    post_views = 600
    score = round(post_views / median, 2)
    
    assert median == 300
    assert score == 2.0