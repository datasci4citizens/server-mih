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

## Image Upload API

The `Image` model now supports file uploads via `POST /api/images/`. Uploaded files are stored in `media/images/YYYY/MM/DD/` (local storage, development only).

Example using cURL (with session cookie or JWT token):

```bash
curl -X POST -F "file=@photo.jpg" \
  -b "sessionid=<SESSION_COOKIE>" \
  http://127.0.0.1:8000/api/images/
```

Response (status 201):
```json
{"id": 1}
```

Files are automatically stored with extension extracted from filename. For production, configure Django to use S3 or object storage via `DEFAULT_FILE_STORAGE` in `settings.py`.

## Testing

Run the test suite:

```bash
export DB_NAME=mi_db DB_USER=mi_user DB_PASSWORD=mi_pass \
  DB_HOST=127.0.0.1 DB_PORT=55432 SECRET_KEY='change-me'
source .venv/bin/activate
python server_mih/manage.py test --verbosity=2
```

Tests include:
- Model creation (Patient, Mih, OMOP Person/Location)
- Authentication (session → JWT exchange, current user endpoint)
- Image upload (multipart/form-data)

Images
-
Uploaded images are stored under the `media/` folder (development). The `Image` model exposes a `file` field and can be uploaded via the API:

Example (use session cookie or `Authorization: Bearer <access>`):

```bash
curl -v -X POST -F "file=@photo.jpg" -b cookie.txt http://127.0.0.1:8000/api/images/
```

Files will be saved to `media/images/YYYY/MM/DD/`. In production use a dedicated object storage and configure Django `DEFAULT_FILE_STORAGE` accordingly.

Documentation
-
I added basic API tests and image upload support. To run tests:

```bash
export DB_NAME=mi_db DB_USER=mi_user DB_PASSWORD=mi_pass DB_HOST=127.0.0.1 DB_PORT=55432 SECRET_KEY='replace-me'
source .venv/bin/activate
python server_mih/manage.py test
```

