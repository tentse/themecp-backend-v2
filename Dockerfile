FROM python:3.12-slim

WORKDIR /app

## No extra OS packages needed


COPY pyproject.toml poetry.lock ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn api.app:api --host 0.0.0.0 --port 8000"]