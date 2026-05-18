#!/bin/sh
set -e

cd /code/server_mih

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn server_mih.wsgi:application --bind 0.0.0.0:8000 --workers 2
