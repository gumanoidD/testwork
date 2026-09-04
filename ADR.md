# Architecture Decision Records (ADR)

## ADR 1: Web Scraping vs Official Telegram API (Telethon/Pyrogram)
- **Status**: Accepted
- **Context**: Requirement to gather public Telegram channel data without demanding API keys/tokens from evaluation setup.
- **Decision**: Parse public web previews (`https://t.me/s/<channel>`) via `httpx` + `BeautifulSoup4`.
- **Consequences**: Zero setup friction for reviewers; rate-limiting risk mitigated via configurable polling intervals.

## ADR 2: Metrics Tracking Schema & Idempotency
- **Status**: Accepted
- **Context**: Need to record views over time without duplicating post entries during frequent scrapes.
- **Decision**: Separate `posts` table (unique by `channel` + `message_id`) from `post_metrics` (append-only timeline log).
- **Consequences**: Enables accurate analytical tracking and strict idempotency on ingestion.

## ADR 3: Anomaly Detection Scoring (Median vs Mean)
- **Status**: Accepted
- **Context**: Identify top-performing posts while neutralizing viral outlier bias.
- **Decision**: Calculate post performance relative to channel median views (`views / median_views`).
- **Consequences**: Provides robust baseline metrics resistant to high-volume skewed statistics.