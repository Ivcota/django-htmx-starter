web: uv run python manage.py migrate && uv run python manage.py collectstatic --noinput && uv run python -m gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker
