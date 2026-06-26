# Nova Infra Utils

A suite of production-hardened web-security toolkits, caching/queue helpers, and GCP operations microservices derived from the **Nova Ecosystem**.

These are standard, reusable infrastructure elements designed for secure and reliable operation on cloud-native environments (such as Google Cloud Run). Each component is independent — import only what you need.

## Features

- **Web Hardening Toolkit** — Redis-backed rate limiting, input/HTML/filepath sanitization, CSP/CORS security headers, upload security (malware + archive-bomb + file-type checks), and request validation middleware.
- **Cache & Job-Queue Helpers** — Redis result caching, Celery-backed background job queue, and `psutil`-based system metrics collection.
- **GCP Operations Microservices** — a daily cost reporter (BigQuery billing → Pub/Sub), a Pub/Sub → Firestore updater, and a distributed health-check service.

## Installation

```bash
pip install nova-infra-utils
```

Components have independent third-party requirements (e.g. `redis`, `bleach`, `python-magic`, `celery`, `google-cloud-*`, `fastapi`/`flask`). Installing the package pulls them in; if you only use one subpackage you can install a slimmer subset yourself.

> **Note:** `python-magic` requires the system `libmagic` library (`brew install libmagic` on macOS, `apt-get install libmagic1` on Debian/Ubuntu).

## Quick Start

### 1. Web Hardening

Rate limiting (async, Redis-backed):

```python
import asyncio
from nova_infra_utils.web_hardening import RateLimiter

async def main():
    limiter = RateLimiter(redis_url="redis://localhost:6379")
    result = await limiter.check_rate_limit(user_id="user-123", endpoint_type="api", tier="free")
    if result["allowed"]:
        await limiter.increment_usage(user_id="user-123", endpoint_type="api", tier="free")
        # ... handle the request ...
    await limiter.close()

asyncio.run(main())
```

Input sanitization (synchronous helpers):

```python
from nova_infra_utils.web_hardening import InputSanitizer

s = InputSanitizer()
safe_html = s.sanitize_html_content("<script>alert(1)</script><b>ok</b>")
safe_path = s.sanitize_file_path("../../etc/passwd")
project   = s.validate_project_name("My Project 01")
```

Security headers on a FastAPI app:

```python
from fastapi import FastAPI
from nova_infra_utils.web_hardening import ValidationMiddleware
from nova_infra_utils.web_hardening.security_headers import configure_security_middleware

app = FastAPI()
configure_security_middleware(app, environment="production")  # CSP / CORS / HSTS
app.add_middleware(ValidationMiddleware)                       # request validation
```

Upload security (async scans before accepting a file):

```python
import asyncio
from nova_infra_utils.web_hardening import UploadSecurity

async def main():
    guard = UploadSecurity(quarantine_dir="/tmp/quarantine")
    clean = await guard.scan_for_malware("/tmp/uploads/file.zip")
    safe  = await guard.check_archive_bomb("/tmp/uploads/file.zip", max_ratio=10, max_size_gb=1)
    if not (clean and safe):
        await guard.quarantine_suspicious_file("/tmp/uploads/file.zip")

asyncio.run(main())
```

### 2. Cache & Job Queue

Redis result cache (async):

```python
import asyncio
from nova_infra_utils.cache_queue import CacheService

async def main():
    cache = CacheService(redis_url="redis://localhost:6379")
    await cache.store_analysis_result(project_id="p1", code_hash="abc123", results={"ok": True}, ttl=86400)
    cached = await cache.get_analysis_result(project_id="p1", code_hash="abc123")
    await cache.close()

asyncio.run(main())
```

Background jobs (Celery broker):

```python
import asyncio
from nova_infra_utils.cache_queue import JobQueue

async def main():
    jobs = JobQueue(broker_url="redis://localhost:6379/0")
    job_id = await jobs.queue_analysis_job(project_data={"repo": "..."}, user_id="user-123")
    status = await jobs.get_job_status(job_id)

asyncio.run(main())
```

### 3. GCP Operations Microservices

These ship as ready-to-deploy entry points rather than libraries you call inline.

**Cost Reporter** — a Pub/Sub-triggered Cloud Function. Deploy `daily_cost_report` as the entry point and trigger it on a schedule (e.g. Cloud Scheduler → Pub/Sub):

```python
from nova_infra_utils.cost_reporter.reporter import daily_cost_report  # (event, context) -> None
```

```bash
gcloud functions deploy daily-cost-report \
  --runtime python312 --entry-point daily_cost_report \
  --trigger-topic nova-cost-reports
```

**Firestore Updater** & **Health Check** — Flask apps intended to run on Cloud Run:

```python
from nova_infra_utils.firestore_updater.updater import app   # Pub/Sub -> Firestore sync
from nova_infra_utils.health_check.checker import app         # distributed health monitor
```

```bash
# served like any Flask/WSGI app
gunicorn -b :8080 nova_infra_utils.firestore_updater.updater:app
```

## License

Licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.

*Note: This open-source package represents generic infrastructure utilities from the Nova Ecosystem. The proprietary autonomous orchestration and Four C's self-regulating engines remain closed-source and patent-pending under DNA Entertainment Ltd.*
