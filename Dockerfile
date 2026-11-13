# The one environment of the project: Python from .python-version (a test checks that the two agree) and the libraries
# pinned in uv.lock. Building the image runs the tests and rebuilds docs/ from the committed data with no network; the
# container then serves the dashboard on http://localhost:8000:
#   docker build -t near-real-usage . && docker run --rm -p 8000:8000 near-real-usage
# Every other command runs in the first stage, the environment, on the repository mounted at /app, so that what it
# writes lands in the repository (the Makefile does this: make test, make offline, make build, make census, ...). That
# stage changes only with uv.lock or the Python version.
FROM python:3.12.12-slim AS env

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /usr/local/bin/uv

# The environment lives outside /app, so mounting the repository there does not hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked \
 && useradd --create-home --shell /usr/sbin/nologin thesis \
 && chown thesis:thesis /app

FROM env
COPY --chown=thesis:thesis . .
USER thesis
RUN python -m pytest -q -p no:cacheprovider && python -m thesis build --offline

EXPOSE 8000
CMD ["python", "-m", "http.server", "8000", "--bind", "0.0.0.0", "--directory", "docs"]
