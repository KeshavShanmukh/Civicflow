# CivicFlow Architecture

## Layers

CivicFlow uses a local-first layered architecture:

- Browser UI: responsive HTML/CSS/JavaScript with same-origin JSON requests.
- HTTP layer: loopback-oriented standard-library HTTP server and secure response headers.
- Use cases: `backend/service.py` contains the core report lifecycle; `backend/platform.py` provides extended identity, profile, duplicate-group, work-order, SLA, search, analytics and administration workflows.
- Data layer: SQLite transactions, normalized tables, indexes, deterministic seed data and migration-safe initialization.
- Offline intelligence: deterministic classification, severity, duplicate scoring and a large local civic knowledge corpus. No vendor model or API key is required.

## Core workflow

Citizen Report → Validation → Duplicate Detection → Categorization → Severity → Priority → Department → Supervisor → Field Worker → Work Order → Resolution → Verification → Notification → Feedback → Analytics.

## Operational boundaries

The bundled server is designed for local development and controlled demonstrations. A public city deployment needs TLS, hardened identity infrastructure, centralized logging, backups, operational monitoring and an independently reviewed threat model.
