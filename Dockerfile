# base image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV HOME_DIR=/app

ENV TZ=Asia/Shanghai
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR ${HOME_DIR}

# 更换国内源 (可选)
RUN rm  -rf /etc/apt/sources.list.d

RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    echo "deb-src https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb-src https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb-src https://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb https://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    echo "deb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# install dependencies
# RUN apt update && apt install -y --fix-missing curl


######## production stage ########
FROM base AS production

# 新建用户
# ENV APP_USER=doc_trans
# RUN useradd -m -s /bin/bash ${APP_USER} \
#     && mkdir -p /tmp \
#     && chown -R ${APP_USER}:${APP_USER} /tmp \
#     && chown -R ${APP_USER}:${APP_USER} ${HOME_DIR}


COPY ./pyproject.toml ${HOME_DIR}/pyproject.toml
COPY ./uv.lock ${HOME_DIR}/uv.lock
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY . ${HOME_DIR}

ENV PATH="${HOME_DIR}/.venv/bin:${PATH}"

EXPOSE 8000

RUN chmod +x ${HOME_DIR}/docker/entrypoint.sh

ENTRYPOINT ["/bin/bash", "-c", "${HOME_DIR}/docker/entrypoint.sh"]
