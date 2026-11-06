# Image for comparing `how` versions. The `how` script is injected at build
# time from a git ref (see build.sh). Never bake API keys into layers.
FROM python:3.11-slim-bookworm

# Re-enable man pages in slim image so `man -P cat <cmd>` local RAG works in container
RUN rm -f /etc/dpkg/dpkg.cfg.d/docker /etc/dpkg/dpkg.cfg.d/excludes \
    && apt-get update && apt-get install -y --no-install-recommends \
        bash coreutils findutils grep sed gawk \
        man-db manpages \
        git procps iproute2 \
        bubblewrap \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /bin/bash howuser

# Optional tldr client (best-effort; not required)
RUN pip install --no-cache-dir tldr 2>/dev/null || true

COPY how /usr/local/bin/how
RUN chmod 755 /usr/local/bin/how

ENV HOW_CONFIG_DIR=/home/howuser/.config/how \
    HOW_CACHE_DIR=/home/howuser/.cache/how \
    HOW_NO_BROWSER=1 \
    HOW_NO_PROMPT=1 \
    CI=1 \
    TESTING=1 \
    HOME=/home/howuser \
    PATH=/usr/local/bin:/usr/bin:/bin

USER howuser
WORKDIR /home/howuser
RUN mkdir -p /home/howuser/.config/how /home/howuser/.cache/how

ENTRYPOINT ["how"]
CMD ["--help"]
