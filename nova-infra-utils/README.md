# Nova Infra Utils

A suite of production-hardened web security toolkits, caching mechanisms, job queues, health checkers, and GCP operation microservices derived from the **Nova Ecosystem**.

These utilities represent standard, reusable infrastructure elements designed for secure and reliable operation on cloud-native environments (such as Google Cloud Run).

## Components

- **Web Hardening Toolkit**: Middleware and filters for rate limiting (Redis-backed), HTML/filepath sanitization, CSP/CORS security headers, upload security (antivirus scans/archive bomb detection), and validation middleware.
- **Cache & Job-Queue Helpers**: Wrappers for Celery task queuing, system metric collectors (utilizing `psutil`), and standard Redis caching helper routines.
- **GCP Cost Reporter**: Daily GCP cost extraction from BigQuery billing tables published to Pub/Sub.
- **Firestore Updater**: Lightweight Pub/Sub to Firestore database synchronization endpoint.
- **Health Check**: Microservice boilerplate for monitoring distributed system statuses.

## License

This package is licensed under the Apache 2.0 License.
