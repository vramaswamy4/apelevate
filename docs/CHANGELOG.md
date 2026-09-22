# Changelog

The refresh of the recovered 2022 app, newest first. `docs/ORIGINAL.md` numbers the problems
(S1, X1, C1, …), and the entries here refer to those numbers.

## Phase 4: README (2026-09-22)

- Rewrote the README for a reader who has never seen the project: what it is, an honest
  history (including what's unknown and why the 2022 layout made deployment hard), how to run
  it, the data model and the rules the database enforces, a problem-then / fix-now table, the
  reasoning behind the refresh (tests, database constraints, payments, the Makefile and Docker,
  configuration, secure defaults, the design system), key decisions, and known limitations.
- Diagrams in README and ORIGINAL.md validated with Mermaid's parser.

## Phase 3: redesign (2026-09-22)

- **Design system** (`static/css/app.css`): one stylesheet, no framework. Colour, spacing,
  radius and type tokens on `:root`; dark theme is a second set of token values (OS preference,
  or a toggle stored in `localStorage`). Components: header and nav, buttons, cards, badges,
  chips, stats, lists, tables that turn into labelled cards on phones, tabs, forms, alerts,
  empty states.
- **Replaced** Bootstrap 5 + Bootstrap 4 + jQuery + Font Awesome (all from CDNs, sometimes on
  the same page) and seven copies of the same inline `<style>` block.
- **Brand kept:** the "AP" monogram is cropped from the 2022 logo and used as a CSS mask, so it
  takes the theme colour; the purple and the amber accent come from the 2022 palette.
- **Accessibility:** every field has a `<label>`; help text and errors are wired to inputs with
  `aria-describedby` / `aria-invalid`; visible focus rings; skip link; `aria-current` on nav;
  contrast checked in both themes (the 2022 white-on-amber buttons were about 1.7:1).
- **htmx** (vendored, 2.0.10) where it removes a page load: enrol (panel, nav balance and
  enrolled count update in place), staff decisions, class filters, and the topic picker.
- **Every page redesigned**, with new copy. Phone fixes found in a browser pass: nav wraps, stats
  two across, the enrol panel comes first on class pages.
- **Screenshots** in `docs/screenshots/` from `make screenshots` (Playwright, throwaway database).
  `docs/screenshots/2022/` shows the original code rendered on its original stack (Django 4.0.6)
  for comparison; no screenshots from 2022 itself survive.

## Phase 2: fix and modernise (2026-09-22)

- **Stack:** Django 4.0.6 → 5.2 LTS on Python 3.12+ (3.13 in Docker and CI). Dependencies
  pinned in `requirements.txt` / `requirements-dev.txt`. Pillow and source-built psycopg2
  dropped; psycopg 3 for PostgreSQL. ruff (lint + format) and pre-commit.
- **Layout:** settings package `APElevate/` → `config/`. The single `APE` app split into
  `accounts`, `catalog`, `classes`, `payments` and `core`. Fresh initial migrations.
- **Settings:** everything environment-specific from env vars (`.env.example`); DEBUG off by
  default; production refuses to start without a secret key; whitenoise; HTTPS hardening behind
  `DJANGO_SECURE`; logging; `check --deploy` clean.
- **Every numbered problem in ORIGINAL.md fixed.** Highlights: server-verified PayPal payments
  and a token ledger (X1); enrolment costs a token, atomically (X2); POST-only state changes
  (X3); real 403s and secure-by-default login (X4); validated private uploads (X5, X6); the
  mentor and student flows work end to end (C1–C5); integer topic numbers (C10); fixed query
  counts on list pages (P1, P2).
- **Built what was stubbed:** subjects browser, profile, mentor analytics (derived from data),
  staff application review with file downloads, class requests.
- **Decisions:** enrolment costs one token (the 2022 purchase page said so; nothing enforced
  it). Accepting an application creates a `MentorProfile` for that subject. Mentor stats are
  computed, not stored. Unused fields dropped: `Mentors.paypal`, `referral_code`,
  `Students.profile_pic`, `Subjects.sub_outline`.
- **Tests:** 169 pytest-django tests, 95% line coverage, passing on SQLite and PostgreSQL 17.
- **Tooling:** `Makefile` (`make dev`, `test`, `lint`, `check`, `up`), `Dockerfile` (non-root,
  gunicorn, static files baked in), `docker-compose.yml` (PostgreSQL), GitHub Actions (lint,
  tests on SQLite and PostgreSQL, deploy checklist, migrations in sync, image build, compose
  smoke test).

## Phase 1: understand and document (2026-09-22)

- Added `docs/ORIGINAL.md`: provenance from the migrations, a page-by-page inventory, the data
  model as an ER diagram, both main flows as they actually run, and 60-odd numbered problems with
  file and line references. The worst ones were confirmed by a scripted run on a fresh database.
- No code changes yet.
