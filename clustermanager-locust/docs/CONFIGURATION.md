# Locust Manager 配置指南

本文档详细介绍了 Locust Manager 的配置选项和最佳实践。

## 目录

- [环境变量配置](#环境变量配置)
- [数据库配置](#数据库配置)
- [Redis 配置](#redis-配置)
- [集群配置](#集群配置)
- [安全配置](#安全配置)
- [性能配置](#性能配置)
- [日志配置](#日志配置)
- [监控配置](#监控配置)
- [配置文件示例](#配置文件示例)

## 环境变量配置

### 基础配置

```bash
# Flask 应用配置
FLASK_ENV=production                    # 运行环境: development, production, testing
FLASK_APP=app.py                       # Flask 应用入口文件
SECRET_KEY=your-secret-key-here        # 会话加密密钥 (必须设置)
DEBUG=False                            # 调试模式 (生产环境必须为 False)

# 服务器配置
HOST=0.0.0.0                          # 监听地址
PORT=5000                              # 监听端口
WORKERS=4                              # Gunicorn worker 进程数
WORKER_CLASS=gevent                    # Worker 类型: sync, gevent, eventlet
WORKER_CONNECTIONS=1000                # 每个 worker 的连接数
MAX_REQUESTS=1000                      # 每个 worker 处理的最大请求数
MAX_REQUESTS_JITTER=100                # 最大请求数的随机偏移
TIMEOUT=30                             # 请求超时时间 (秒)
KEEPALIVE=2                            # Keep-alive 超时时间 (秒)
```

### 数据库配置

```bash
# MySQL/MariaDB 配置
DATABASE_URL=mysql://user:password@host:port/database
# 或者分别配置
DB_HOST=localhost                      # 数据库主机
DB_PORT=3306                          # 数据库端口
DB_USER=locust_user                   # 数据库用户名
DB_PASSWORD=your_password             # 数据库密码
DB_NAME=locust_manager                # 数据库名称
DB_CHARSET=utf8mb4                    # 字符集

# 连接池配置
DB_POOL_SIZE=20                       # 连接池大小
DB_POOL_TIMEOUT=30                    # 连接超时时间
DB_POOL_RECYCLE=3600                  # 连接回收时间 (秒)
DB_POOL_PRE_PING=True                 # 连接前测试
DB_MAX_OVERFLOW=10                    # 最大溢出连接数

# SQLAlchemy 配置
SQLALCHEMY_TRACK_MODIFICATIONS=False  # 禁用对象修改跟踪
SQLALCHEMY_RECORD_QUERIES=False       # 禁用查询记录 (生产环境)
SQLALCHEMY_ECHO=False                 # 禁用 SQL 日志 (生产环境)
```

### Redis 配置

```bash
# Redis 连接配置
REDIS_URL=redis://password@host:port/db
# 或者分别配置
REDIS_HOST=localhost                  # Redis 主机
REDIS_PORT=6379                       # Redis 端口
REDIS_PASSWORD=your_password          # Redis 密码
REDIS_DB=0                           # Redis 数据库编号

# Redis 连接池配置
REDIS_MAX_CONNECTIONS=50              # 最大连接数
REDIS_RETRY_ON_TIMEOUT=True          # 超时重试
REDIS_SOCKET_TIMEOUT=5               # Socket 超时时间
REDIS_SOCKET_CONNECT_TIMEOUT=5       # 连接超时时间
REDIS_HEALTH_CHECK_INTERVAL=30       # 健康检查间隔

# Redis 集群配置 (如果使用集群)
REDIS_CLUSTER_NODES=host1:port1,host2:port2,host3:port3
REDIS_CLUSTER_SKIP_FULL_COVERAGE_CHECK=True
```

### 文件存储配置

```bash
# 文件路径配置
UPLOAD_FOLDER=uploads                 # 上传文件目录
SCRIPTS_FOLDER=scripts               # 脚本文件目录
LOGS_FOLDER=logs                     # 日志文件目录
TEMP_FOLDER=temp                     # 临时文件目录

# 文件大小限制
MAX_CONTENT_LENGTH=16777216          # 最大上传文件大小 (16MB)
MAX_SCRIPT_SIZE=1048576              # 最大脚本文件大小 (1MB)

# 允许的文件类型
ALLOWED_SCRIPT_EXTENSIONS=py,txt     # 允许的脚本文件扩展名
ALLOWED_UPLOAD_EXTENSIONS=py,txt,json,yaml,yml  # 允许的上传文件扩展名

# 文件清理配置
CLEANUP_INTERVAL=3600                # 清理间隔 (秒)
TEMP_FILE_LIFETIME=1800              # 临时文件生存时间 (秒)
LOG_FILE_RETENTION=30                # 日志文件保留天数
```

### 集群配置

```bash
# 集群基础配置
CLUSTER_ENABLED=True                 # 启用集群模式
CLUSTER_NODE_ID=node-1               # 节点 ID (唯一)
CLUSTER_NODE_NAME=locust-manager-1   # 节点名称
CLUSTER_NODE_TYPE=master             # 节点类型: master, worker

# 集群发现配置
CLUSTER_DISCOVERY_METHOD=static      # 发现方法: static, consul, etcd, k8s
CLUSTER_NODES=node1:5000,node2:5000,node3:5000  # 静态节点列表

# 集群通信配置
CLUSTER_BIND_HOST=0.0.0.0           # 集群绑定地址
CLUSTER_BIND_PORT=5001              # 集群通信端口
CLUSTER_HEARTBEAT_INTERVAL=10       # 心跳间隔 (秒)
CLUSTER_HEARTBEAT_TIMEOUT=30        # 心跳超时 (秒)
CLUSTER_ELECTION_TIMEOUT=15         # 选举超时 (秒)

# 负载均衡配置
CLUSTER_LOAD_BALANCE_METHOD=round_robin  # 负载均衡方法
CLUSTER_MAX_TASKS_PER_NODE=100      # 每个节点最大任务数
CLUSTER_TASK_DISTRIBUTION_STRATEGY=even  # 任务分发策略
```

### 安全配置

```bash
# 认证配置
AUTH_ENABLED=True                    # 启用认证
AUTH_METHOD=local                    # 认证方法: local, ldap, oauth
SESSION_TIMEOUT=3600                 # 会话超时时间 (秒)
PASSWORD_MIN_LENGTH=8                # 密码最小长度
PASSWORD_REQUIRE_SPECIAL=True        # 密码需要特殊字符

# CORS 配置
CORS_ENABLED=True                    # 启用 CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com  # 允许的源
CORS_METHODS=GET,POST,PUT,DELETE     # 允许的方法
CORS_HEADERS=Content-Type,Authorization  # 允许的头部

# 安全头配置
SECURITY_HEADERS_ENABLED=True        # 启用安全头
CSP_ENABLED=True                     # 启用内容安全策略
HSTS_ENABLED=True                    # 启用 HSTS
HSTS_MAX_AGE=31536000               # HSTS 最大年龄

# IP 限制配置
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com  # 允许的主机
RATE_LIMIT_ENABLED=True              # 启用速率限制
RATE_LIMIT_DEFAULT=100/hour          # 默认速率限制
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1  # 速率限制存储
```

### 监控配置

```bash
# 指标配置
METRICS_ENABLED=True                 # 启用指标收集
METRICS_PORT=9090                    # 指标端口
METRICS_PATH=/metrics                # 指标路径
METRICS_NAMESPACE=locust_manager     # 指标命名空间

# 健康检查配置
HEALTH_CHECK_ENABLED=True            # 启用健康检查
HEALTH_CHECK_PATH=/health            # 健康检查路径
HEALTH_CHECK_INTERVAL=30             # 健康检查间隔 (秒)

# 追踪配置
TRACING_ENABLED=False                # 启用分布式追踪
TRACING_SAMPLER_TYPE=const           # 采样器类型
TRACING_SAMPLER_PARAM=1              # 采样参数
JAEGER_AGENT_HOST=localhost          # Jaeger Agent 主机
JAEGER_AGENT_PORT=6831               # Jaeger Agent 端口
```

## 数据库配置

### MySQL/MariaDB 优化

#### 服务器配置 (my.cnf)

```ini
[mysqld]
# 基础配置
port = 3306
bind-address = 0.0.0.0
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
default-time-zone = '+00:00'

# 内存配置
innodb_buffer_pool_size = 1G         # 缓冲池大小 (推荐总内存的 70-80%)
innodb_log_file_size = 256M          # 日志文件大小
innodb_log_buffer_size = 16M         # 日志缓冲区大小
key_buffer_size = 256M               # MyISAM 键缓冲区大小
query_cache_size = 64M               # 查询缓存大小
query_cache_limit = 2M               # 查询缓存限制

# 连接配置
max_connections = 200                # 最大连接数
max_connect_errors = 1000           # 最大连接错误数
connect_timeout = 10                # 连接超时时间
wait_timeout = 600                  # 等待超时时间
interactive_timeout = 600           # 交互超时时间

# InnoDB 配置
innodb_file_per_table = 1           # 每表一个文件
innodb_flush_log_at_trx_commit = 2  # 事务提交时刷新日志
innodb_flush_method = O_DIRECT      # 刷新方法
innodb_lock_wait_timeout = 50       # 锁等待超时时间

# 日志配置
slow_query_log = 1                  # 启用慢查询日志
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2                 # 慢查询时间阈值
log_queries_not_using_indexes = 1   # 记录未使用索引的查询

# 二进制日志配置
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW
expire_logs_days = 7
max_binlog_size = 100M
```

#### 数据库初始化脚本

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS locust_manager 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER IF NOT EXISTS 'locust_user'@'%' IDENTIFIED BY 'your_password';
CREATE USER IF NOT EXISTS 'locust_user'@'localhost' IDENTIFIED BY 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON locust_manager.* TO 'locust_user'@'%';
GRANT ALL PRIVILEGES ON locust_manager.* TO 'locust_user'@'localhost';

-- 创建只读用户 (用于监控)
CREATE USER IF NOT EXISTS 'locust_readonly'@'%' IDENTIFIED BY 'readonly_password';
GRANT SELECT ON locust_manager.* TO 'locust_readonly'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 优化设置
SET GLOBAL innodb_buffer_pool_size = 1073741824;  -- 1GB
SET GLOBAL max_connections = 200;
SET GLOBAL query_cache_size = 67108864;  -- 64MB
```

### PostgreSQL 配置 (可选)

#### 服务器配置 (postgresql.conf)

```ini
# 连接配置
listen_addresses = '*'
port = 5432
max_connections = 200
superuser_reserved_connections = 3

# 内存配置
shared_buffers = 256MB              # 共享缓冲区
effective_cache_size = 1GB          # 有效缓存大小
work_mem = 4MB                      # 工作内存
maintenance_work_mem = 64MB         # 维护工作内存

# WAL 配置
wal_level = replica
max_wal_size = 1GB
min_wal_size = 80MB
checkpoint_completion_target = 0.9

# 日志配置
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_min_duration_statement = 1000   # 记录超过 1 秒的查询
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

## Redis 配置

### 基础配置 (redis.conf)

```ini
# 网络配置
bind 0.0.0.0
port 6379
protected-mode yes
requirepass your_redis_password

# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru        # 内存不足时的淘汰策略

# 持久化配置
save 900 1                          # 900 秒内至少 1 个键变化时保存
save 300 10                         # 300 秒内至少 10 个键变化时保存
save 60 10000                       # 60 秒内至少 10000 个键变化时保存

# AOF 配置
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# 客户端配置
timeout 300                         # 客户端空闲超时时间
tcp-keepalive 300                   # TCP keepalive 时间
maxclients 10000                    # 最大客户端连接数

# 日志配置
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled yes
syslog-ident redis

# 安全配置
rename-command FLUSHDB ""           # 禁用危险命令
rename-command FLUSHALL ""
rename-command KEYS ""
rename-command CONFIG "CONFIG_9a8b7c6d5e4f3g2h1i"  # 重命名敏感命令
```

### Redis 集群配置

```ini
# 集群配置
cluster-enabled yes
cluster-config-file nodes-6379.conf
cluster-node-timeout 15000
cluster-announce-ip 192.168.1.100
cluster-announce-port 6379
cluster-announce-bus-port 16379

# 集群故障转移
cluster-require-full-coverage no
cluster-migration-barrier 1
```

## 集群配置

### Kubernetes 集群配置

#### ConfigMap 配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: locust-manager-config
data:
  # 应用配置
  FLASK_ENV: "production"
  CLUSTER_ENABLED: "true"
  CLUSTER_DISCOVERY_METHOD: "k8s"
  
  # 数据库配置
  DB_HOST: "mysql"
  DB_PORT: "3306"
  DB_NAME: "locust_manager"
  DB_CHARSET: "utf8mb4"
  
  # Redis 配置
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
  
  # 文件配置
  UPLOAD_FOLDER: "/app/uploads"
  SCRIPTS_FOLDER: "/app/scripts"
  LOGS_FOLDER: "/app/logs"
  
  # 监控配置
  METRICS_ENABLED: "true"
  HEALTH_CHECK_ENABLED: "true"
```

#### Secret 配置

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: locust-manager-secrets
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret-key>
  DB_PASSWORD: <base64-encoded-db-password>
  REDIS_PASSWORD: <base64-encoded-redis-password>
```

### Docker Swarm 配置

#### Stack 配置

```yaml
version: '3.8'

services:
  locust-manager:
    image: locust-manager:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - CLUSTER_ENABLED=true
      - CLUSTER_DISCOVERY_METHOD=swarm
    networks:
      - locust-network
    volumes:
      - uploads:/app/uploads
      - scripts:/app/scripts
      - logs:/app/logs

networks:
  locust-network:
    driver: overlay
    attachable: true

volumes:
  uploads:
  scripts:
  logs:
```

## 安全配置

### SSL/TLS 配置

#### Nginx SSL 配置

```nginx
server {
    listen 443 ssl http2;
    server_name locust-manager.example.com;

    # SSL 证书配置
    ssl_certificate /etc/ssl/certs/locust-manager.crt;
    ssl_certificate_key /etc/ssl/private/locust-manager.key;
    ssl_trusted_certificate /etc/ssl/certs/ca-bundle.crt;

    # SSL 协议和加密套件
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_ecdh_curve secp384r1;

    # SSL 会话配置
    ssl_session_timeout 10m;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # 安全头
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';";

    location / {
        proxy_pass http://locust-manager;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
}
```

### 防火墙配置

#### UFW 配置

```bash
# 重置防火墙规则
ufw --force reset

# 默认策略
ufw default deny incoming
ufw default allow outgoing

# 允许 SSH
ufw allow 22/tcp

# 允许 HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 允许应用端口 (仅内网)
ufw allow from 10.0.0.0/8 to any port 5000
ufw allow from 172.16.0.0/12 to any port 5000
ufw allow from 192.168.0.0/16 to any port 5000

# 允许数据库端口 (仅内网)
ufw allow from 10.0.0.0/8 to any port 3306
ufw allow from 10.0.0.0/8 to any port 6379

# 启用防火墙
ufw enable
```

#### iptables 配置

```bash
#!/bin/bash
# iptables 防火墙配置脚本

# 清空现有规则
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# 设置默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许 SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许应用端口 (仅内网)
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 5000 -j ACCEPT
iptables -A INPUT -p tcp -s 172.16.0.0/12 --dport 5000 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 5000 -j ACCEPT

# 允许数据库端口 (仅内网)
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 3306 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 6379 -j ACCEPT

# 防止 DDoS 攻击
iptables -A INPUT -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables/rules.v4
```

## 性能配置

### 应用性能配置

#### Gunicorn 配置

```python
# gunicorn.conf.py
import multiprocessing

# 服务器配置
bind = "0.0.0.0:5000"
backlog = 2048

# Worker 配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# 超时配置
timeout = 30
keepalive = 2
graceful_timeout = 30

# 日志配置
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程配置
user = "appuser"
group = "appuser"
tmp_upload_dir = "/tmp"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
```

#### uWSGI 配置

```ini
[uwsgi]
# 应用配置
module = app:app
callable = app

# 服务器配置
http = 0.0.0.0:5000
master = true
processes = 4
threads = 2
enable-threads = true

# 性能配置
buffer-size = 32768
post-buffering = 8192
harakiri = 30
max-requests = 1000
max-worker-lifetime = 3600
reload-on-rss = 512
worker-reload-mercy = 60

# 日志配置
logto = /app/logs/uwsgi.log
log-maxsize = 50000000
log-backupcount = 5

# 安全配置
uid = appuser
gid = appuser
chmod-socket = 666
vacuum = true
die-on-term = true
```

### 缓存配置

#### Redis 缓存配置

```python
# cache_config.py
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/1',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'locust_manager:',
    'CACHE_OPTIONS': {
        'connection_pool_kwargs': {
            'max_connections': 50,
            'retry_on_timeout': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }
    }
}

# 缓存策略配置
CACHE_STRATEGIES = {
    'dashboard_data': {
        'timeout': 60,
        'key_prefix': 'dashboard:'
    },
    'task_list': {
        'timeout': 30,
        'key_prefix': 'tasks:'
    },
    'instance_list': {
        'timeout': 15,
        'key_prefix': 'instances:'
    },
    'cluster_status': {
        'timeout': 10,
        'key_prefix': 'cluster:'
    }
}
```

#### Memcached 配置 (可选)

```python
# memcached_config.py
CACHE_CONFIG = {
    'CACHE_TYPE': 'memcached',
    'CACHE_MEMCACHED_SERVERS': ['127.0.0.1:11211'],
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'locust_manager:',
    'CACHE_OPTIONS': {
        'behaviors': {
            'tcp_nodelay': True,
            'ketama': True
        }
    }
}
```

## 日志配置

### 应用日志配置

```python
# logging_config.py
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': os.path.join('logs', 'app.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': os.path.join('logs', 'error.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'json_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': os.path.join('logs', 'app.json'),
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'encoding': 'utf8'
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'locust_manager': {
            'handlers': ['console', 'file', 'json_file'],
            'level': 'INFO',
            'propagate': False
        },
        'sqlalchemy.engine': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        },
        'werkzeug': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}
```

### 系统日志配置

#### rsyslog 配置

```bash
# /etc/rsyslog.d/50-locust-manager.conf
# Locust Manager 日志配置

# 应用日志
:programname, isequal, "locust-manager" /var/log/locust-manager/app.log
& stop

# 错误日志
:programname, isequal, "locust-manager" :severity, isequal, "error" /var/log/locust-manager/error.log
& stop

# 访问日志
:programname, isequal, "nginx" :msg, contains, "locust-manager" /var/log/locust-manager/access.log
& stop
```

#### logrotate 配置

```bash
# /etc/logrotate.d/locust-manager
/var/log/locust-manager/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    sharedscripts
    postrotate
        systemctl reload locust-manager
        systemctl reload nginx
    endscript
}

/app/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    copytruncate
}
```

## 监控配置

### Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "locust_manager_rules.yml"

scrape_configs:
  - job_name: 'locust-manager'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: /metrics
    scrape_interval: 10s
    scrape_timeout: 5s

  - job_name: 'locust-manager-cluster'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - locust-manager
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: locust-manager
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 告警规则配置

```yaml
# locust_manager_rules.yml
groups:
  - name: locust_manager
    rules:
      - alert: LocustManagerDown
        expr: up{job="locust-manager"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Locust Manager instance is down"
          description: "Locust Manager instance {{ $labels.instance }} has been down for more than 1 minute."

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second on {{ $labels.instance }}."

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s on {{ $labels.instance }}."

      - alert: DatabaseConnectionFailure
        expr: database_connections_failed_total > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Database connection failures detected on {{ $labels.instance }}."

      - alert: RedisConnectionFailure
        expr: redis_connections_failed_total > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failure"
          description: "Redis connection failures detected on {{ $labels.instance }}."

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 512
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}MB on {{ $labels.instance }}."

      - alert: DiskSpaceLow
        expr: disk_free_bytes / disk_total_bytes < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk space is {{ $value | humanizePercentage }} full on {{ $labels.instance }}."
```

## 配置文件示例

### 开发环境配置

```bash
# .env.development
FLASK_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# 数据库配置
DATABASE_URL=mysql://locust_user:password@localhost:3306/locust_manager_dev
DB_POOL_SIZE=5
DB_POOL_TIMEOUT=10

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# 文件配置
UPLOAD_FOLDER=uploads
SCRIPTS_FOLDER=scripts
LOGS_FOLDER=logs
MAX_CONTENT_LENGTH=16777216

# 集群配置
CLUSTER_ENABLED=False

# 安全配置
AUTH_ENABLED=False
CORS_ENABLED=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# 监控配置
METRICS_ENABLED=True
HEALTH_CHECK_ENABLED=True

# 日志配置
LOG_LEVEL=DEBUG
```

### 测试环境配置

```bash
# .env.testing
FLASK_ENV=testing
DEBUG=False
TESTING=True
SECRET_KEY=test-secret-key

# 数据库配置
DATABASE_URL=mysql://locust_user:password@localhost:3306/locust_manager_test
DB_POOL_SIZE=3

# Redis 配置
REDIS_URL=redis://localhost:6379/1

# 文件配置
UPLOAD_FOLDER=test_uploads
SCRIPTS_FOLDER=test_scripts
LOGS_FOLDER=test_logs

# 集群配置
CLUSTER_ENABLED=False

# 安全配置
AUTH_ENABLED=True
CORS_ENABLED=True

# 监控配置
METRICS_ENABLED=False
HEALTH_CHECK_ENABLED=True

# 日志配置
LOG_LEVEL=INFO
```

### 生产环境配置

```bash
# .env.production
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-production-secret-key-here

# 数据库配置
DATABASE_URL=mysql://locust_user:secure_password@db-cluster:3306/locust_manager
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=True

# Redis 配置
REDIS_URL=redis://:secure_password@redis-cluster:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_RETRY_ON_TIMEOUT=True

# 文件配置
UPLOAD_FOLDER=/app/uploads
SCRIPTS_FOLDER=/app/scripts
LOGS_FOLDER=/app/logs
MAX_CONTENT_LENGTH=16777216

# 集群配置
CLUSTER_ENABLED=True
CLUSTER_NODE_ID=node-1
CLUSTER_DISCOVERY_METHOD=k8s
CLUSTER_HEARTBEAT_INTERVAL=10

# 安全配置
AUTH_ENABLED=True
CORS_ENABLED=True
CORS_ORIGINS=https://locust-manager.example.com
ALLOWED_HOSTS=locust-manager.example.com
RATE_LIMIT_ENABLED=True
SECURITY_HEADERS_ENABLED=True

# 监控配置
METRICS_ENABLED=True
HEALTH_CHECK_ENABLED=True
TRACING_ENABLED=True

# 日志配置
LOG_LEVEL=INFO
```

### Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  locust-manager:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql://locust_user:${MYSQL_PASSWORD}@mysql:3306/locust_manager
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CLUSTER_ENABLED=false
    volumes:
      - uploads:/app/uploads
      - scripts:/app/scripts
      - logs:/app/logs
    depends_on:
      - mysql
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=locust_manager
      - MYSQL_USER=locust_user
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./config/mysql.cnf:/etc/mysql/conf.d/custom.cnf
    ports:
      - "3306:3306"
    restart: unless-stopped
    command: --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - locust-manager
    restart: unless-stopped

volumes:
  uploads:
  scripts:
  logs:
  mysql_data:
  redis_data:
```

这个配置指南涵盖了 Locust Manager 的所有主要配置选项。根据你的具体部署环境和需求，选择合适的配置选项并进行相应的调整。记住在生产环境中要特别注意安全配置和性能优化。