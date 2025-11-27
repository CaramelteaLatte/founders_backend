# Repository Guidelines

## Project Structure & Module Organization
The repository is intentionally small: `qcc.py` houses the Selenium workflow that logs into Qichacha, searches for a company, and saves screenshots; keep ChromeDriver-compatible assets nearby when iterating on that module. `test_nested.py` contains the `ShareholderCalculator` reference implementation plus sample data and acts as the canonical place for regression tests. `nested_judge.py` is reserved for a future CLI entry point—treat it as the staging area for orchestration code that wires calculator logic with scraping output.

## Build, Test, and Development Commands
Create a virtual environment before installing browser automation libraries:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip selenium pytest
```
Run the crawler with a concrete query, e.g. `python3 qcc.py "宇树科技"`, which opens Chrome, injects cookies, and writes screenshots to the desktop. Execute the analytical sample script via `python3 test_nested.py` to print shareholder breakdowns. For fast regressions prefer `python3 -m pytest -q` so failures point to exact assertions.

## Coding Style & Naming Conventions
Use 4-space indentation, type hints, and docstrings similar to the ones already in `test_nested.py`. Functions and variables stay in `snake_case`, while classes follow `PascalCase`. Keep Selenium locators and magic numbers near the code that uses them and guard external resources with helper functions so future agents can swap credentials without touching core logic.

## Testing Guidelines
Pytest is the default runner. Add new fixtures or parametrized cases under `test_nested.py` (or additional `test_*.py` files) that mirror realistic multi-layer shareholder scenarios. Name tests after the scenario they validate (e.g., `test_cross_holdings_loop_guard`). Target 90% branch coverage for calculator utilities and at least smoke coverage for scraper helper functions using mocks rather than real browser calls.

## Commit & Pull Request Guidelines
Write commits in the form `type: short imperative summary` (e.g., `feat: expand shareholder cache`). Each PR should describe the motivation, outline manual test evidence (commands + output snippets), and link any tracked issues. Include screenshots only when UI-facing scraper output changes; otherwise attach log excerpts proving browser automation still works.

## Security & Configuration Tips
Never commit live Qichacha cookies or API tokens; load them via environment variables or an ignored JSON secrets file and call `add_cookies_to_driver` with that payload. Clear proxy variables, as `qcc.py` already does, and document any machine-specific Chrome flags inside the README instead of hard-coding them. When sharing artifacts, redact company names unless the stakeholder has approved their disclosure.
