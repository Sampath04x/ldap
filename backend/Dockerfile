FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml || pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg[binary] alembic pydantic pydantic-settings faker click python-multipart httpx pytest pytest-asyncio anyio
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
