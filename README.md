# APElevate

A marketplace for AP-exam tutoring, built in 2022 while I was in high school: students sign up, browse subjects and units, buy tokens and enrol in mentor-led Zoom classes; mentors apply, get approved, create classes and track hours, students and revenue. Django 4.0, one app (`APE`), server-rendered templates, SQLite in development. It ran on PythonAnywhere and later Heroku.

Recovered from a 2023 export and pushed here in September 2026. A full refresh (current Django, tests, security fixes, new UI) is in progress; this commit is the original code with the secrets removed.

## Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```
