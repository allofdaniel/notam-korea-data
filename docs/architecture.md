# Architecture

## Core Flow

```text
Korea AIM source
  -> direct HTTP collector
  -> optional Selenium fallback
  -> local SQLite persistence
  -> change detection
  -> downstream API or hosted delivery
```

## Main Scripts

- `notam_crawler_api.py`: primary HTTP collector
- `notam_crawler.py`: browser automation fallback
- `notam_hybrid_crawler.py`: coordinates primary and fallback collection
- `notam_change_detector.py`: compares current and previous NOTAM records
- `notam_monitor.py`: end-to-end workflow for crawl + change tracking

## Data Model

The local SQLite workflow centers on `notam_records` and `crawl_logs`.

The schema directory also contains PostgreSQL and SQLite DDL drafts for more structured deployments.
