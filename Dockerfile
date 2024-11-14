# base image
FROM python:3.10-slim-bookworm AS base

# TODO: set HOME_DIR
ENV HOME_DIR=/app/project_name

WORKDIR ${HOME_DIR}
ENV POETRY_VERSION=1.8.3
RUN pip install --no-cache-dir poetry==${POETRY_VERSION} -i https://mirrors.aliyun.com/pypi/simple/
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true
ENV POETRY_REQUESTS_TIMEOUT=15


# install packages
FROM base AS packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc g++ libc-dev libffi-dev libgmp-dev libmpfr-dev libmpc-dev libpq-dev
COPY pyproject.toml poetry.lock ./
RUN poetry install --sync --no-cache --no-root


# production stage
FROM base AS production
EXPOSE 8000
ENV TZ=Asia/Shanghai
ENV VIRTUAL_ENV=${HOME_DIR}/.venv
COPY --from=packages ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
COPY . ${HOME_DIR}
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
