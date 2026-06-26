# Nova Ecosystem - Open Source Core

[![License](https://img.shields.io/badge/License-Apache_2.0-orange.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Nova Ecosystem](https://img.shields.io/badge/Ecosystem-Nova-orange.svg)](https://github.com/dnaent/nova-ecosystem)

Welcome to the official open-source repository for the core infrastructure packages of the **Nova Ecosystem**.

**The core open-source infrastructure of the Nova Ecosystem. An enterprise-grade LLM orchestration engine featuring context-aware token budgeting and zero-downtime provider failover for multi-agent systems.**

Derived directly from our proprietary enterprise app-factory backend, these tools provide standard, production-ready libraries for multi-agent networking, event telemetry, and highly-resilient multi-vendor LLM orchestration.

---

## 🚀 Launch & Marketing Assets
Check out the [`marketing-assets/`](marketing-assets/) directory for our launch graphics, explainer slides, and failover logic animations.

---

## 📦 Packages

This monorepo houses the following three foundational packages:

### 1. [Nova LLM Router](file:///Users/Phantom/Desktop/DNAENT™/Nova_Ecosystem/nova-package/nova-llm-router)
A highly-resilient, multi-vendor LLM routing engine featuring context-aware token budgeting and automatic cross-provider failover.
- **Failover Logic:** Seamless hot-swaps on `429 Rate Limit` or service timeouts (e.g., Anthropic → Gemini).
- **Token Budgeting:** Explicit context execution limits enforced via native Python `contextvars` to prevent costly runaway agent self-correction loops.
- **Unified Interface:** Standardized invocation syntax across Anthropic, OpenAI, and Google Gemini.

### 2. [Nova Agent SDK](file:///Users/Phantom/Desktop/DNAENT™/Nova_Ecosystem/nova-package/nova-agent-sdk)
The event-driven messaging and telemetry backend powering autonomous agent collaboration.
- **Event Mesh:** Native wrapper around Google Cloud Pub/Sub for clean, asynchronous inter-agent messaging.
- **Telemetry:** Standardized auditing, logging, and performance metrics schemas.
- **Secure Config:** Seamless integration with GCP Secret Manager for dynamic runtime configuration.

### 3. [Nova Infra Utils](file:///Users/Phantom/Desktop/DNAENT™/Nova_Ecosystem/nova-package/nova-infra-utils)
A suite of production-hardened web security toolkits, caching mechanisms, job queues, health checkers, and GCP operations microservices.
- **Web Hardening**: Secure middleware for Redis-backed rate limiting, bleach-based HTML sanitization, CSP/CORS headers, and upload validation.
- **Cache & Queue**: Helpers for standard Redis caches, Celery background jobs, and psutil-based resource tracking.
- **Operation microservices**: Standardized microservice logic for Daily GCP Cost reporting, Firestore updates via Pub/Sub, and distributed health check monitors.


---

## 🎨 System Architecture

```text
                               +-----------------------------------+
                               |         Nova Dashboard UI         |
                               +-------------------+---------------+
                                                   |
+-----------------------+      +-------------------+---------------+      +-----------------------+
|    Nova Agent SDK     |<---->|        Nova LLM Router            |<---->|   Nova Infra Utils    |
| (Events & Telemetry)  |      |   (Multi-vendor Orchestration)    |      | (Security & Caching)  |
+-----------------------+      +---------+------------------+------+      +-----------------------+
                                         |                  |
                       (429/500 Failover)|                  | (Token Budgeting)
                                         v                  v
                               +---------+----+    +--------+------+
                               | Anthropic AI |    | Google Gemini |
                               +--------------+    +---------------+
```

---

## 🛡️ License & Intellectual Property

The core libraries in this repository are licensed under the **Apache 2.0 License**—see the individual package directories for details.

> [!NOTE]
> This open-source repository represents the communication, telemetry, and LLM routing foundation of the Nova Ecosystem. The proprietary autonomous orchestration and Four C's self-regulating engines remain closed-source and patent-pending under DNA Entertainment Ltd.
