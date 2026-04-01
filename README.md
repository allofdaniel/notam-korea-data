# Korean NOTAM Data

[![CI](https://github.com/allofdaniel/notam-korea-data/actions/workflows/ci.yml/badge.svg)](https://github.com/allofdaniel/notam-korea-data/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Open-source tooling for collecting, normalizing, and monitoring Korean NOTAM data.

Korea does not currently offer an easy public developer-facing NOTAM API. This project is an attempt to close that gap with reusable collection and monitoring code that other developers can build on.

## Why This Exists

- Korean NOTAM data matters for flight safety, research, and aviation software.
- Access is still difficult for independent developers and small teams.
- Structured, self-hostable tooling is more useful than a manual-only web workflow.

This repository focuses on the open-source core:

- direct collection from Korea AIM NOTAM endpoints
- optional Selenium fallback
- local persistence in SQLite
- change detection and monitoring workflows

## Project Status

This is an active infrastructure project, not a polished SDK.

- The direct crawler is the main path.
- The Selenium crawler is a fallback path.
- The monitoring flow is intended for local or self-hosted experimentation.
- Hosted/commercial delivery can exist separately on top of the same core.

## Managed Service

A separate hosted landing page exists here:

- https://notam-api-landing.vercel.app/

That hosted service direction does not conflict with the open-source core. The OSS value is in the collector, parser, schema, and self-hostable building blocks.

## Repository Layout

```text
.
├── notam_crawler_api.py
├── notam_crawler.py
├── notam_hybrid_crawler.py
├── notam_change_detector.py
├── notam_monitor.py
├── database/
│   ├── schema.sql
│   └── schema_sqlite.sql
├── docs/
│   ├── architecture.md
│   └── roadmap.md
└── examples/
    └── sample_notams.json
```

## Quick Start

### Base setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Direct crawler

```bash
python notam_crawler_api.py
```

### Hybrid crawler

If you want the Selenium fallback too:

```bash
pip install -r requirements-selenium.txt
python notam_hybrid_crawler.py
```

### Monitor workflow

```bash
python notam_monitor.py
```

## Important Notes

- This is not an official government API.
- Upstream source systems and response formats can change.
- Fetched NOTAM data may still be subject to the original source system's terms.
- Do not use this repository as the sole source for operational flight briefing or safety-critical decision making. Verify against official sources.

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Contributing

Contributions are welcome, especially around:

- parser accuracy
- API contract design
- documentation
- better tests
- Korean aviation data validation

## License

MIT. See [LICENSE](LICENSE).
