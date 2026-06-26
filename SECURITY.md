# Security Policy

## Supported versions

This repository tracks the latest released version of each package
(`nova-llm-router`, `nova-agent-sdk`, `nova-infra-utils`). Security fixes are
applied to the `main` branch and the most recent release.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them privately via one of:

- GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
  ("Report a vulnerability" under the **Security** tab), or
- email **security@dnaent.co.uk**.

Please include:

- the affected package and version,
- a description of the issue and its impact,
- steps to reproduce (a minimal proof-of-concept if possible).

We aim to acknowledge reports within **3 business days** and to provide a remediation
timeline after triage. Please give us a reasonable window to release a fix before any
public disclosure.

## Scope

`nova-infra-utils` includes security middleware (rate limiting, sanitization, upload
scanning). These are defense-in-depth building blocks, not a substitute for a complete
security review of your own deployment. Reports about weaknesses in these utilities are
especially welcome.
