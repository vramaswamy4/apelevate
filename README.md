# APElevate

A marketplace for AP-exam tutoring, built in 2022 while I was in high school: students sign up, browse subjects and units, buy tokens and enrol in mentor-led Zoom classes; mentors apply, get approved, create classes and track hours, students and revenue. Django 4.0, one app (`APE`), server-rendered templates, SQLite in development. It ran on PythonAnywhere and later Heroku.

Recovered from a 2023 export and pushed here in September 2026. A refresh (current Django, tests, security fixes, new UI) is in progress.

## Run

```bash
make dev      # creates .venv, installs pinned deps, migrates SQLite, seeds demo data, runs :8000
make test     # pytest
make up       # the same app on PostgreSQL with docker compose
```

Demo accounts (password `apelevate-demo`): `student@apelevate.test`, `mentor@apelevate.test`,
`admin@apelevate.test`. A full write-up is coming; `docs/ORIGINAL.md` documents the 2022 code.
