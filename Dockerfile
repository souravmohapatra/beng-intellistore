FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=1000:1000 . /app
RUN python manage.py collectstatic --noinput

USER 1000:1000
ENTRYPOINT ["python", "manage.py"]
