#!/bin/sh
set -e

echo "Attente de la base de données..."
python - <<'PY'
import sys
import time

import django
from django.db import connection
from django.db.utils import OperationalError

django.setup()
for attempt in range(30):
    try:
        connection.ensure_connection()
        break
    except OperationalError:
        time.sleep(2)
else:
    sys.exit("Base de données injoignable.")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${SEED_REFERENCE:-0}" = "1" ]; then
    python manage.py seed_reference
fi
if [ "${SEED_DEMO:-0}" = "1" ]; then
    python manage.py seed_demo
fi

exec "$@"
