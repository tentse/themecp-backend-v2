FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y


COPY pyproject.toml poetry.lock ./app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn pecha_api.app:api --host 0.0.0.0 --port 8000"]