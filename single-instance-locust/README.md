# Single Instance Locust

A production-grade load testing tool built on Locust. It supports multi-account concurrency, HMAC-SHA256 authentication, an easy-to-use Web UI, Docker-based deployment, and hot-loading of test scripts.

## Features

- Multi-account support with simple load balancing
- Built-in HMAC-SHA256 signing for secure API calls
- Web UI for script upload, selection, and test control
- Script hot-loading without rebuilding the Docker image
- Real-time status and metrics through Locust’s native UI
- Multiple deployment options: local, Docker, Docker Compose, Kubernetes

## Quick Start

### Requirements

- Python `3.10+` (recommended: `3.10.11`)
- `pip`
- Docker (optional, for containerized deployment)

### Local Installation

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:8088
```

### Docker

```bash
# Build image
docker build -t single-instance-locust:latest .

# Run container
docker run --rm -p 8088:8088 single-instance-locust:latest
# Open http://localhost:8088
```

## Web UI Guide

The Web UI streamlines development and testing by allowing you to upload and switch Locust scripts without rebuilding or restarting services.

### Interface Overview

- Service status indicator (Running/Stopped)
- Script management: upload `.py`, list, select, delete
- Test configuration: target host, script selection
- Control actions: start/stop Locust, open Locust native UI

### Typical Workflow

1. Prepare your test script (save as `.py`).
2. Upload the script via the Web UI (drag-and-drop or file picker).
3. Select the target host and choose the uploaded script.
4. Start the Locust service (status indicator turns green when running).
5. Open the Locust native UI and configure `Number of users` and `Spawn rate`.
6. Monitor metrics (RPS, response time, failure rate) and iterate on scripts as needed.

### Example Script

```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def test_api(self):
        self.client.get("/api/health")
```

## Script Development Guide

### Basic Structure

```python
from locust import HttpUser, task, between
import json
import random

# Example user accounts for testing
test_accounts = [
    {"username": "user1", "password": "password1", "user_id": "001"},
    {"username": "user2", "password": "password2", "user_id": "002"},
]

class APIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a user starts - typically used for login"""
        self.account = random.choice(test_accounts)
        self.login()

    def login(self):
        """Login to get authentication token"""
        login_url = "/api/auth/login"
        payload = {
            "username": self.account["username"],
            "password": self.account["password"]
        }
        with self.client.post(login_url, json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token")
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                resp.success()
            else:
                resp.failure(f"Login failed: {resp.text}")

    @task(3)
    def get_user_profile(self):
        """High frequency task - get user profile"""
        if not hasattr(self, "headers"):
            return
        
        with self.client.get(
            f"/api/users/{self.account['user_id']}",
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Get profile failed: {resp.text}")

    @task(1)
    def update_settings(self):
        """Low frequency task - update user settings"""
        if not hasattr(self, "headers"):
            return
            
        payload = {"setting": "value", "timestamp": "2024-01-01"}
        with self.client.put(
            "/api/users/settings",
            headers=self.headers,
            json=payload,
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Update failed: {resp.text}")
```

### Best Practices

- Avoid hardcoding secrets; use environment variables (e.g., `API_KEY`)
- Use `@task(weight)` to control task frequency
- Include error handling; use `catch_response=True` and mark success/failure explicitly
- Keep `wait_time` reasonable to simulate realistic pacing

## Configuration

Set via environment variables or `.env` file:

- `TARGET_HOST`: Target server base URL (e.g., `https://api.dev.example.com`)
- `LOCUST_FILE`: Path to the selected script (e.g., `Trader/trader_locust.py`)
- `WEB_PORT`: Web UI port (default: `8088`)
- `LOG_LEVEL`: Log verbosity (`DEBUG`, `INFO`, etc.)

## Deployment

### Local Development

```bash
python -m venv venv
venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
python app.py
# Open http://localhost:8088
```

### Docker (Single Container)

```bash
docker build -t single-instance-locust:latest .
docker run --rm -p 8088:8088 single-instance-locust:latest

# With environment variables
docker run --rm \
  -p 8088:8088 \
  -e TARGET_HOST=https://api.dev.example.com \
  -e LOCUST_FILE=Trader/trader_locust.py \
  single-instance-locust:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  locust-web:
    build: .
    ports:
      - "8088:8088"
    environment:
      - TARGET_HOST=https://api.dev.example.com
      - LOCUST_FILE=Trader/trader_locust.py
      - WEB_PORT=8088
    volumes:
      - ./scripts:/app/scripts
      - ./logs:/app/logs
    restart: unless-stopped
```

### Kubernetes

Use the provided manifests to deploy on K8s. Configure environment variables, resource limits, and volumes for `scripts/` and `logs/` according to your cluster setup.

## Troubleshooting

- Script import errors: ensure all required packages are listed in `requirements.txt`
- Syntax errors: run `python -m pyflakes <script.py>` before uploading
- Port conflicts: change `WEB_PORT` if `8088` is in use
- Locust not starting: verify `LOCUST_FILE` points to a valid `.py` script

## Usage Restrictions

This software is explicitly prohibited from use by the following individuals or organizations. Any direct or indirect use by these parties constitutes infringement and is strictly forbidden:

- Any officials, employees, or representatives of the Government of the Islamic Republic of Iran
- Any individuals, organizations, or affiliates controlled or directly influenced by Iranian religious authorities, including but not limited to Shia clerics, religious foundations, religious councils/committees, and their associated organizations
- The Government of the Democratic People’s Republic of Korea (North Korea) or its agents
- Members and related personnel of the following organizations, including but not limited to:
  - Hamas
  - Ansar Allah (Houthi movement / Yemen)
- Any groups designated as terrorist organizations by the United Nations, the European Union, the United States, or the People’s Republic of China, and their members

By using this software, you confirm that you do not belong to, represent, or act on behalf of any of the entities listed above.

## Notes

- For advanced examples, organize scripts under `scripts/` by scenario or environment.
- Logs are stored under `logs/`. Mount volumes in container deployments to persist logs.
- For production, consider resource limits and health checks (Docker/Compose/K8s).