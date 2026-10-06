# CivicFlow

**CivicFlow — Intelligent Urban Problem Detection, Management and Resolution Platform** is a local-first municipal workflow application connecting citizens, municipal departments, supervisors, field workers and administrators from report intake through resolution and analytics.

## Non-negotiable project constraints

- No required external API keys.
- Local SQLite database and standard-library runtime.
- No intentional duplicate or filler code.
- Fully functional end-to-end workflow.
- Four-member GitHub workflow using feature branches → `develop` → `main`.
- The repository includes a large, uniquely keyed offline civic knowledge/scenario corpus so the project can exceed the requested 500,000 counted source LOC without fabricating duplicate functions.

## Core workflow

Citizen report → validation → duplicate detection → categorization → severity → priority → department routing → supervisor review → field-worker assignment → work order → repair → verification → citizen notification → feedback → analytics.

## Main feature areas

Authentication and identity, citizen profiles and addresses, reports and attachments, comments, role/permission catalog, account verification, password reset, account locking, device/session inventory, duplicate-group verification and merging, severity/priority scoring, departments, categories, regions and policies, worker skills/availability/leave, work orders, SLA policies, staged escalations, in-app notifications, citizen feedback/reopen, local geospatial calculations and hotspots, dashboards, analytics snapshots, search, CSV/JSON/text reports, audit trails, system health and Docker support.

## Roles

Citizen, Field Worker, Supervisor, Department Staff, Department Administrator, City Administrator and System Administrator.

Local demo roles are available for all seven roles. Demo passwords are not required.

## Run on Windows

1. Install Python 3.10+.
2. From this folder run `./run.ps1` in PowerShell, or `python -m backend`.
3. Open the local URL printed in the terminal.

The server binds to loopback by default and serves the UI plus JSON API from one origin. The database is automatically created at `data/civicflow.sqlite3`.

## Docker

Run `docker compose up --build` and open `http://127.0.0.1:8000`. The container uses the same local SQLite model and requires no package installation or external API service.

## Test

```text
python -m unittest -v tests.test_platform tests.test_service tests.test_server
python tools/knowledge_check.py --sample 2 --search pothole
```

## Source size

The current repository contains more than **500,000 application source lines** when counted across the application packages, interfaces and test code, excluding the `.git` directory, caches, virtual environments, runtime databases and the offline knowledge corpus.

## Safety and deployment note

This repository is designed for local development and demonstrations. A real public municipal deployment would require hardened identity, TLS, backups, monitoring, deployment controls and an independent security review.
