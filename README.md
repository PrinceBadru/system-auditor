# System Auditor

System Auditor is a project for examining systems and infrastructure, identifying
opportunities for improvement, and presenting useful, environment-specific
insights.

## Project status

This repository currently contains a minimal Python package scaffold and a
passing smoke test. Auditing capabilities are not implemented yet.

## Development

Requires Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
```

GitHub Actions runs Ruff lint and format checks plus the unit tests on Python
3.11, 3.12, and 3.13.

## Intended direction

The project aims to help people understand the systems they operate by:

- examining an environment and its configuration;
- highlighting potential issues and improvement opportunities; and
- producing clear findings relevant to the environment that was examined.

The exact supported environments, audit checks, and report formats will be
defined as the project develops.

## Architecture decisions

The reasoning behind significant project choices is recorded in
[docs/adr](docs/adr/README.md).

## License

This project is licensed under the [MIT License](LICENSE).
