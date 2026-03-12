# Claude Code Instructions — Microbiome Tracker v2

## Workflow rules

After rolling out any code change:

1. **Update tests** — add or update tests in `tests/` to cover the new behaviour. Run `python3 -m pytest` and confirm all tests pass before considering the task done.
2. **Update `README.md`** — add a summary of the change to the "Recent Changes" section (create the section if it doesn't exist). Also update any other README sections that reference the changed behaviour (e.g. test count, architecture notes).

## Project conventions

- Item display names are always **lowercase** (enforced by `get_display_name` in `item_service.py`).
- New food/plant synonyms go in `CANONICAL_MAPPINGS`; accented display forms go in `_DISPLAY_OVERRIDES`; new canonical items go in `KNOWN_ITEMS`. All three live in `backend/app/services/item_service.py`.
- Tests use an in-memory SQLite database via `StaticPool` — no Docker or API keys needed to run them.
- Deploy to production with `fly deploy`. The production database is Neon PostgreSQL; local dev uses SQLite.
