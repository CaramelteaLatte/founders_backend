# Repository Guidelines

## Project Structure & Module Organization
Root-level scripts (`company_pipeline.py`, `amac.py`, `neris.py`, `wenshu.py`, `zxgk/zxgk.py`) cover each data source, while orchestration happens inside `company_pipeline.py`. Shareholding logic, Selenium helpers, and simulators live in `nested_judge/`; treat `test_nested.py` as the canonical reference for the `ShareholderCalculator`. Every crawler writes JSON + screenshots to `~/Desktop/<公司名>/`, so reuse that layout whenever you add exporters or redact artifacts.

## Build, Test, and Development Commands
Provision dependencies inside a virtual environment before touching Selenium or requests code:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Run the blended workflow via `python company_pipeline.py "宇树科技"`; exercise individual scrapers with `python nested_judge/qcc_nested.py "宇树科技"`, `python wenshu.py "借款纠纷"`, or `python zxgk/zxgk.py "大连热电"`. Keep `requirements.txt` authoritative and rerun `pip install -r requirements.txt` whenever dependencies change so reproducible builds stay trivial.

## Coding Style & Naming Conventions
Follow standard Python rules: 4-space indentation, `snake_case` naming, and constants in `UPPER_SNAKE_CASE`. Match the docstring + type-hint depth used in `test_nested.py`, keeping Selenium selectors and wait times inside helper functions. Never embed cookies or tokens; inject them via loader functions or environment variables so scripts remain shareable.

## Testing Guidelines
Prefer `pytest` for anything beyond manual smoke checks; `python -m pytest nested_judge/test_nested.py -q` must stay green before touching calculator logic or parsers. Name tests after the rule they validate (`test_three_level_penetration`, `test_cookie_expiry_guard`) and feed them sanitized JSON exports. Target ~80% coverage for pure-Python utilities and keep at least one stubbed smoke test per scraper so refactors do not silently break CLI entry points.

## Commit & Pull Request Guidelines
The working tree is distributed without `.git`, but upstream history follows a conventional-commit format (`type(scope): short imperative summary`, e.g., `feat(nested_judge): cache qcc tokens`). Keep subjects under 72 characters and capture user impact plus risk in the body when needed. Pull requests should link the ticket, paste the commands you ran (with output snippets or screenshot paths), and mention any credential or cookie prerequisites so reviewers can replay the change.

## Security & Configuration Tips
Never check in live Qichacha cookies, CSRC credentials, or Chrome profiles; load them from ignored files or environment variables and document the schema in the README or PR. The scripts already clear proxy settings, so record local overrides in PR notes instead of committing them. Treat the `~/Desktop/<公司名>/` artifacts as sensitive data and scrub company names before sharing screenshots outside the core delivery group.
