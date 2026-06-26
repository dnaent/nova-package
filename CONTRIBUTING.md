# Contributing to Nova Open Source Core

Thanks for your interest in contributing! This repository is a monorepo of three
independent, production-derived packages: `nova-llm-router`, `nova-agent-sdk`, and
`nova-infra-utils`.

## Development setup

Each package is installable on its own. Work in a virtual environment:

```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip pytest

# install the package you're working on (editable)
pip install -e ./nova-llm-router        # or ./nova-agent-sdk, ./nova-infra-utils
```

> `nova-infra-utils` depends on `python-magic`, which needs the system `libmagic`
> library: `brew install libmagic` (macOS) / `apt-get install libmagic1` (Debian/Ubuntu).

## Running tests

```bash
pytest nova-llm-router/tests
pytest nova-infra-utils/tests
```

CI runs these on Python 3.10–3.12 for every pull request.

## Guidelines

- **Scope:** keep changes to a single package per PR where possible.
- **Style:** match the surrounding code; keep public APIs stable or call out breaking changes.
- **Tests:** add or update tests for any behaviour change. Tests must not require
  network access, API keys, or cloud credentials.
- **Commits:** use clear, conventional-style messages (e.g. `fix(llm-router): ...`).
- **Scope boundary:** this repo is the open-source *foundation*. The proprietary
  autonomous orchestration and Four C's engines are intentionally **not** part of it —
  please don't add code that depends on them.

## Reporting bugs / requesting features

Open an issue using the templates in `.github/ISSUE_TEMPLATE/`. For security issues,
**do not open a public issue** — see [SECURITY.md](./SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](./LICENSE).
