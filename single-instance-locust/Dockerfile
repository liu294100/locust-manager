# Lightweight Python base image
FROM python:3.10.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies first for better layer caching
ARG PIP_INDEX_URL
COPY requirements.txt ./
# Install dependencies without using any proxy; if PIP_INDEX_URL is provided, use it as mirror
RUN if [ -n "$PIP_INDEX_URL" ]; then \
      env -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy -u ALL_PROXY -u all_proxy -u NO_PROXY -u no_proxy python -m pip install --no-cache-dir -r requirements.txt -i "$PIP_INDEX_URL"; \
    else \
      env -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy -u ALL_PROXY -u all_proxy -u NO_PROXY -u no_proxy python -m pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy source code
COPY . .

# Expose ports: 8088 for management UI, 8089 for Locust web UI
EXPOSE 8088 8089

# Default variables (can be overridden at runtime)
ENV LOCUST_FILE=Trader/trader_locust.py \
    TARGET_HOST=

# Run Flask management interface by default
CMD ["python", "app.py"]