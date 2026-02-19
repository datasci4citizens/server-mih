Django scaffold for server-mih migration

Quick start:

1. Create a virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables (optional for Postgres):

```bash
export DB_NAME=yourdb
export DB_USER=youruser
export DB_PASSWORD=yourpass
export DB_HOST=localhost
export DB_PORT=5432
export SECRET_KEY='replace-me'
```

3. Run migrations and start server:

```bash
python manage.py migrate
python manage.py runserver
```

This scaffold adds an app `mih` with models mirroring the current FastAPI schemas. Next: map models to OMOP and implement OAuth.
