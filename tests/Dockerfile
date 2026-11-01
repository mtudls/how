# Lightweight local test environment for `how` CI/CD & V&V testing
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    ruff \
    flake8 \
    bandit

COPY . /app

# Default command: runs the complete verification suite locally
CMD ["bash", "-c", "python -m py_compile how tests/test_vv_suite.py tests/test_safety.py tests/test_ab_bench.py scripts/ai_architect_review.py && bash -n install.sh && ruff check how && flake8 how --max-line-length=120 --extend-ignore=E501,E402,E722,F401,F841,E302,E305 && bandit -r how -ll --skip B310,B603,B607 && python tests/test_vv_suite.py && python tests/test_safety.py"]
