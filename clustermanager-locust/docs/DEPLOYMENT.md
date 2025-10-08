# Locust Manager 部署指南

本文档提供了 Locust Manager 的详细部署指南，包括本地开发、Docker 容器化部署和 Kubernetes 集群部署。

## 目录

- [环境准备](#环境准备)
- [本地开发部署](#本地开发部署)
- [Docker 部署](#docker-部署)
- [Kubernetes 部署](#kubernetes-部署)
- [生产环境配置](#生产环境配置)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## 环境准备

### 系统要求

#### 最低配置
- CPU: 2 核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 操作系统: Linux (Ubuntu 18.04+, CentOS 7+), macOS, Windows 10+

#### 推荐配置
- CPU: 4+ 核心
- 内存: 8GB+ RAM
- 存储: 50GB+ SSD
- 网络: 1Gbps

### 软件依赖

#### 基础依赖
- Python 3.8+
- pip 21.0+
- Git 2.20+

#### 数据库
- MySQL 5.7+ 或 MariaDB 10.3+
- Redis 5.0+

#### 容器化 (可选)
- Docker 20.0+
- Docker Compose 1.29+

#### 集群部署 (可选)
- Kubernetes 1.20+
- kubectl 1.20+
- Helm 3.0+ (可选)

## 本地开发部署

### 1. 克隆项目

```bash
git clone https://github.com/your-username/locust-manager.git
cd locust-manager
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 使用 conda
conda create -n locust-manager python=3.9
conda activate locust-manager
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

#### 环境变量配置示例

```bash
# Flask 配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True

# 数据库配置
DATABASE_URL=mysql://locust_user:password@localhost:3306/locust_manager

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 文件存储配置
UPLOAD_FOLDER=uploads
SCRIPTS_FOLDER=scripts
LOGS_FOLDER=logs

# 集群配置
CLUSTER_ENABLED=false
CLUSTER_NODE_ID=node-1

# 安全配置
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

### 5. 设置数据库

#### MySQL/MariaDB 设置

```sql
-- 创建数据库
CREATE DATABASE locust_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'locust_user'@'localhost' IDENTIFIED BY 'your_password';
CREATE USER 'locust_user'@'%' IDENTIFIED BY 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON locust_manager.* TO 'locust_user'@'localhost';
GRANT ALL PRIVILEGES ON locust_manager.* TO 'locust_user'@'%';
FLUSH PRIVILEGES;
```

#### 初始化数据库

```bash
# 初始化数据库表
python manage.py init-db

# 创建管理员用户 (可选)
python manage.py create-admin --username admin --email admin@example.com
```

### 6. 启动服务

```bash
# 启动 Redis (如果未运行)
redis-server

# 启动应用
python app.py
```

访问 http://localhost:5000 查看应用。

### 7. 开发工具 (可选)

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 代码格式化
black .
isort .

# 代码检查
flake8 .
mypy .
```

## Docker 部署

### 1. 使用 Docker Compose (推荐)

#### 启动所有服务

```bash
# 构建并启动
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f locust-manager
```

#### 服务配置

`docker-compose.yml` 包含以下服务：

- **locust-manager**: 主应用服务
- **mysql**: MySQL 数据库
- **redis**: Redis 缓存
- **nginx**: 反向代理 (可选)

#### 环境变量配置

编辑 `.env` 文件：

```bash
# 数据库配置
MYSQL_ROOT_PASSWORD=root_password
MYSQL_DATABASE=locust_manager
MYSQL_USER=locust_user
MYSQL_PASSWORD=user_password

# Redis 配置
REDIS_PASSWORD=redis_password

# 应用配置
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
```

#### 数据持久化

```bash
# 查看数据卷
docker volume ls

# 备份数据
docker-compose exec mysql mysqldump -u root -p locust_manager > backup.sql

# 恢复数据
docker-compose exec -T mysql mysql -u root -p locust_manager < backup.sql
```

### 2. 单独构建和运行

#### 构建镜像

```bash
# 构建应用镜像
docker build -t locust-manager:latest .

# 构建特定版本
docker build -t locust-manager:v1.0.0 .
```

#### 运行容器

```bash
# 启动 MySQL
docker run -d \
  --name locust-mysql \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -e MYSQL_DATABASE=locust_manager \
  -e MYSQL_USER=locust_user \
  -e MYSQL_PASSWORD=user_password \
  -v mysql_data:/var/lib/mysql \
  -p 3306:3306 \
  mysql:8.0

# 启动 Redis
docker run -d \
  --name locust-redis \
  -v redis_data:/data \
  -p 6379:6379 \
  redis:7-alpine

# 启动应用
docker run -d \
  --name locust-manager \
  --link locust-mysql:mysql \
  --link locust-redis:redis \
  -e DATABASE_URL=mysql://locust_user:user_password@mysql:3306/locust_manager \
  -e REDIS_URL=redis://redis:6379/0 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/scripts:/app/scripts \
  -v $(pwd)/logs:/app/logs \
  -p 5000:5000 \
  locust-manager:latest
```

### 3. 多阶段构建优化

#### 生产环境 Dockerfile

```dockerfile
# 多阶段构建示例
FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.9-slim

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser

# 复制依赖
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# 复制应用代码
WORKDIR /app
COPY --chown=appuser:appuser . .

# 创建必要目录
RUN mkdir -p uploads scripts logs && \
    chown -R appuser:appuser uploads scripts logs

USER appuser

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
```

## Kubernetes 部署

### 1. 准备工作

#### 检查集群状态

```bash
# 检查集群连接
kubectl cluster-info

# 检查节点状态
kubectl get nodes

# 检查存储类
kubectl get storageclass
```

#### 创建命名空间

```bash
kubectl create namespace locust-manager
kubectl config set-context --current --namespace=locust-manager
```

### 2. 配置存储

#### 持久化存储配置

```yaml
# k8s/storage.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: locust-manager-uploads-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: locust-manager-storage
  nfs:
    server: nfs-server.example.com
    path: /exports/locust-manager/uploads
```

#### 部署存储

```bash
kubectl apply -f k8s/storage.yaml
```

### 3. 配置密钥和配置

#### 创建 Secret

```bash
# 从文件创建
kubectl create secret generic locust-manager-secrets \
  --from-literal=mysql-root-password=root_password \
  --from-literal=mysql-password=user_password \
  --from-literal=redis-password=redis_password \
  --from-literal=secret-key=your-secret-key

# 从 .env 文件创建
kubectl create secret generic locust-manager-env --from-env-file=.env
```

#### 创建 ConfigMap

```bash
kubectl create configmap locust-manager-config \
  --from-literal=FLASK_ENV=production \
  --from-literal=CLUSTER_ENABLED=true \
  --from-literal=UPLOAD_FOLDER=/app/uploads \
  --from-literal=SCRIPTS_FOLDER=/app/scripts \
  --from-literal=LOGS_FOLDER=/app/logs
```

### 4. 部署数据库和缓存

#### MySQL 部署

```yaml
# k8s/mysql.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: locust-manager-secrets
              key: mysql-root-password
        - name: MYSQL_DATABASE
          value: locust_manager
        - name: MYSQL_USER
          value: locust_user
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: locust-manager-secrets
              key: mysql-password
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
```

#### Redis 部署

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: locust-manager-secrets
              key: redis-password
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-data-pvc
```

### 5. 部署应用

#### 应用部署配置

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-manager
spec:
  replicas: 3
  selector:
    matchLabels:
      app: locust-manager
  template:
    metadata:
      labels:
        app: locust-manager
    spec:
      serviceAccountName: locust-manager
      containers:
      - name: locust-manager
        image: locust-manager:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          value: mysql://locust_user:$(MYSQL_PASSWORD)@mysql:3306/locust_manager
        - name: REDIS_URL
          value: redis://:$(REDIS_PASSWORD)@redis:6379/0
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: locust-manager-secrets
              key: mysql-password
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: locust-manager-secrets
              key: redis-password
        envFrom:
        - configMapRef:
            name: locust-manager-config
        - secretRef:
            name: locust-manager-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
        - name: scripts
          mountPath: /app/scripts
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: locust-manager-uploads-pvc
      - name: scripts
        persistentVolumeClaim:
          claimName: locust-manager-scripts-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: locust-manager-logs-pvc
```

### 6. 配置服务和入口

#### Service 配置

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: locust-manager
spec:
  selector:
    app: locust-manager
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: locust-manager-headless
spec:
  clusterIP: None
  selector:
    app: locust-manager
  ports:
  - port: 5000
    targetPort: 5000
```

#### Ingress 配置

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: locust-manager
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - locust-manager.example.com
    secretName: locust-manager-tls
  rules:
  - host: locust-manager.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: locust-manager
            port:
              number: 80
```

### 7. 使用部署脚本

#### 自动化部署

```bash
# 安装
./k8s/deploy.sh install

# 升级
./k8s/deploy.sh upgrade

# 卸载
./k8s/deploy.sh uninstall

# 查看状态
./k8s/deploy.sh status

# 查看日志
./k8s/deploy.sh logs
```

#### 部署脚本功能

- 自动检查依赖
- 创建命名空间和 RBAC
- 部署存储、数据库、缓存
- 部署应用和服务
- 配置监控和日志
- 健康检查和状态报告

### 8. Helm 部署 (可选)

#### 创建 Helm Chart

```bash
# 创建 Chart
helm create locust-manager-chart

# 安装
helm install locust-manager ./locust-manager-chart

# 升级
helm upgrade locust-manager ./locust-manager-chart

# 卸载
helm uninstall locust-manager
```

#### Values 配置

```yaml
# values.yaml
replicaCount: 3

image:
  repository: locust-manager
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: locust-manager.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

mysql:
  enabled: true
  auth:
    rootPassword: root_password
    database: locust_manager
    username: locust_user
    password: user_password

redis:
  enabled: true
  auth:
    password: redis_password
```

## 生产环境配置

### 1. 安全配置

#### SSL/TLS 配置

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name locust-manager.example.com;

    ssl_certificate /etc/ssl/certs/locust-manager.crt;
    ssl_certificate_key /etc/ssl/private/locust-manager.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://locust-manager;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 防火墙配置

```bash
# UFW 配置
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# iptables 配置
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -j DROP
```

### 2. 性能优化

#### 数据库优化

```sql
-- MySQL 配置优化
SET GLOBAL innodb_buffer_pool_size = 1073741824;  -- 1GB
SET GLOBAL max_connections = 200;
SET GLOBAL query_cache_size = 67108864;  -- 64MB
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 2;
```

#### Redis 优化

```bash
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### 应用优化

```python
# config.py
class ProductionConfig:
    DEBUG = False
    TESTING = False
    
    # 数据库连接池
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Redis 连接池
    REDIS_CONNECTION_POOL = {
        'max_connections': 50,
        'retry_on_timeout': True
    }
    
    # 缓存配置
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300
```

### 3. 监控配置

#### Prometheus 监控

```yaml
# monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'locust-manager'
      static_configs:
      - targets: ['locust-manager:5000']
      metrics_path: /metrics
```

#### Grafana 仪表板

```json
{
  "dashboard": {
    "title": "Locust Manager Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### 4. 日志配置

#### 日志聚合

```yaml
# logging/fluentd.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
```

#### 日志配置

```python
# logging_config.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO'
        }
    }
}
```

## 监控和日志

### 1. 健康检查

#### 应用健康检查

```python
# health.py
@app.route('/health')
def health_check():
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'disk_space': check_disk_space(),
        'memory': check_memory()
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    })
```

#### Kubernetes 健康检查

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### 2. 指标收集

#### 应用指标

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_TASKS = Gauge('locust_active_tasks', 'Number of active tasks')
ACTIVE_INSTANCES = Gauge('locust_active_instances', 'Number of active instances')
```

#### 系统指标

```bash
# 使用 node_exporter
docker run -d \
  --name node_exporter \
  -p 9100:9100 \
  -v "/proc:/host/proc:ro" \
  -v "/sys:/host/sys:ro" \
  -v "/:/rootfs:ro" \
  prom/node-exporter
```

### 3. 日志管理

#### 日志轮转

```bash
# logrotate 配置
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    postrotate
        systemctl reload locust-manager
    endscript
}
```

#### 日志分析

```bash
# 使用 ELK Stack
docker-compose -f elk-stack.yml up -d

# 查看错误日志
grep "ERROR" logs/app.log | tail -20

# 分析访问模式
awk '{print $1}' logs/access.log | sort | uniq -c | sort -nr
```

## 故障排除

### 1. 常见问题

#### 数据库连接问题

```bash
# 检查数据库状态
systemctl status mysql
docker-compose logs mysql

# 测试连接
mysql -h localhost -u locust_user -p locust_manager

# 检查权限
SHOW GRANTS FOR 'locust_user'@'%';
```

#### Redis 连接问题

```bash
# 检查 Redis 状态
systemctl status redis
docker-compose logs redis

# 测试连接
redis-cli -h localhost -p 6379 ping

# 检查内存使用
redis-cli info memory
```

#### 应用启动问题

```bash
# 检查日志
tail -f logs/app.log
docker-compose logs -f locust-manager

# 检查端口占用
netstat -tlnp | grep 5000
lsof -i :5000

# 检查环境变量
env | grep FLASK
```

### 2. 性能问题

#### 数据库性能

```sql
-- 查看慢查询
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

-- 查看连接数
SHOW STATUS LIKE 'Threads_connected';

-- 查看缓存命中率
SHOW STATUS LIKE 'Qcache_hits';
SHOW STATUS LIKE 'Qcache_inserts';
```

#### 应用性能

```python
# 性能分析
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# 运行代码
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(10)
```

#### 内存泄漏

```bash
# 使用 memory_profiler
pip install memory-profiler
python -m memory_profiler app.py

# 使用 objgraph
import objgraph
objgraph.show_most_common_types()
objgraph.show_growth()
```

### 3. 网络问题

#### 连接测试

```bash
# 测试端口连通性
telnet localhost 5000
nc -zv localhost 5000

# 检查防火墙
ufw status
iptables -L

# 检查 DNS 解析
nslookup locust-manager.example.com
dig locust-manager.example.com
```

#### 负载均衡

```bash
# 检查 Nginx 状态
nginx -t
systemctl status nginx

# 查看 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 4. Kubernetes 问题

#### Pod 问题

```bash
# 查看 Pod 状态
kubectl get pods -o wide
kubectl describe pod locust-manager-xxx

# 查看 Pod 日志
kubectl logs locust-manager-xxx
kubectl logs -f locust-manager-xxx --previous

# 进入 Pod 调试
kubectl exec -it locust-manager-xxx -- /bin/bash
```

#### 服务问题

```bash
# 查看服务状态
kubectl get svc
kubectl describe svc locust-manager

# 测试服务连通性
kubectl run test-pod --image=busybox --rm -it -- /bin/sh
wget -qO- http://locust-manager/health
```

#### 存储问题

```bash
# 查看 PV/PVC 状态
kubectl get pv,pvc
kubectl describe pvc locust-manager-uploads-pvc

# 检查存储类
kubectl get storageclass
kubectl describe storageclass locust-manager-storage
```

### 5. 备份和恢复

#### 数据备份

```bash
# MySQL 备份
mysqldump -u root -p locust_manager > backup_$(date +%Y%m%d).sql

# Redis 备份
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb backup_redis_$(date +%Y%m%d).rdb

# 文件备份
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
tar -czf scripts_backup_$(date +%Y%m%d).tar.gz scripts/
```

#### 数据恢复

```bash
# MySQL 恢复
mysql -u root -p locust_manager < backup_20240101.sql

# Redis 恢复
systemctl stop redis
cp backup_redis_20240101.rdb /var/lib/redis/dump.rdb
systemctl start redis

# 文件恢复
tar -xzf uploads_backup_20240101.tar.gz
tar -xzf scripts_backup_20240101.tar.gz
```

## 总结

本部署指南涵盖了 Locust Manager 的完整部署流程，从本地开发到生产环境的各种部署方式。根据你的具体需求选择合适的部署方案：

- **本地开发**: 使用虚拟环境和本地数据库
- **小规模部署**: 使用 Docker Compose
- **生产环境**: 使用 Kubernetes 集群
- **企业级部署**: 结合监控、日志、备份等完整方案

在部署过程中，请注意：

1. 根据实际负载调整资源配置
2. 定期备份重要数据
3. 监控系统性能和健康状态
4. 及时更新安全补丁
5. 建立完善的运维流程

如有问题，请参考故障排除章节或联系技术支持。