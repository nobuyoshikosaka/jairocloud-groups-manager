# syntax=docker/dockerfile:1

# === Base image with Python and user setup ===
FROM python:3.14-slim AS base

ARG USERNAME=pyuser
ARG GROUPNAME=pyuser
ARG UID=1000
ARG GID=1000

WORKDIR /code
RUN pip install -U pip && pip install uv

RUN groupadd -g ${GID} ${GROUPNAME} && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME}
RUN chown ${USERNAME}:${GROUPNAME} /code
USER ${USERNAME}


# === Install Python dependencies ===
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen


# === Development server for Flask app ===
FROM base AS dev

ENV VIRTUAL_ENV="/code/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=deps --chown=${USERNAME}:${GROUPNAME} /code/.venv ./.venv
COPY --chown=${USERNAME}:${GROUPNAME} . .

RUN uv pip install -e .

ENV FLASK_ENV=development
ENV FLASK_APP="server.app"
ENV FLASK_RUN_HOST="0.0.0.0"
ENV FLASK_RUN_PORT=5050
ENV FLASK_DEBUG=1
EXPOSE 5050
CMD ["flask", "run", "--reload"]
