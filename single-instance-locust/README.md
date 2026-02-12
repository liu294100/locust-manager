# Chief StressTest Locust

基于 Locust 的企业级压力测试工具，支持多账号并发测试、智能签名认证和可视化管理界面。

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [Web UI 使用指南](#web-ui-使用指南)
- [脚本开发指南](#脚本开发指南)
- [部署方式](#部署方式)
- [配置说明](#配置说明)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)
- [API 参考](#api-参考)

## 🚀 功能特性

- **多账号支持**: 支持配置多个测试账号，自动负载均衡
- **智能认证**: 内置 HMAC-SHA256 签名认证机制
- **可视化界面**: 提供 Web UI 进行脚本管理和测试监控
- **Docker 支持**: 支持容器化部署，便于 CI/CD 集成
- **脚本热加载**: 支持动态上传和切换测试脚本
- **实时监控**: 实时显示测试状态和性能指标
- **多环境支持**: 支持开发、测试、生产环境配置

## 🏃‍♂️ 快速开始

### 环境要求

- Python 3.10+ (推荐 3.10.11)
- pip 包管理器
- Docker (可选，用于容器化部署)

### 本地安装

1. **克隆项目**
```bash
git clone https://dev.stx365.com/chief/chief-stresstest-locust.git
cd chief-stresstest-locust
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动 Web UI**
```bash
python app.py
```

4. **访问界面**
打开浏览器访问 [http://localhost:8088](http://localhost:8088)

### Docker 快速部署

```bash
# 构建镜像
docker build -t chief-stresstest-locust:latest .

# 启动服务
docker run --rm -p 8088:8088 chief-stresstest-locust:latest

# 访问 http://localhost:8088
```

## 🖥️ Web UI 使用指南

### 核心优势

Web UI 的脚本上传功能为开发和测试带来显著便利：

#### 🚀 节省部署时间
- **无需重新构建镜像**：直接通过界面上传脚本，避免修改代码后重新构建 Docker 镜像
- **即时生效**：上传后立即可用，无需重启服务或重新部署
- **快速迭代**：支持脚本的快速修改和测试，大幅缩短开发周期

#### 🛠️ 方便开发测试
- **可视化管理**：通过 Web 界面直观管理所有测试脚本
- **多脚本切换**：轻松在不同测试场景间切换，无需修改配置文件
- **实时调试**：开发人员可以快速上传新版本脚本进行测试验证
- **团队协作**：团队成员可以共享和交换测试脚本，提高协作效率

#### 📈 提升开发效率
- **降低技术门槛**：无需了解 Docker 或部署流程，专注于脚本开发
- **减少环境依赖**：避免本地环境配置问题，统一使用 Web 环境
- **快速验证**：新功能开发完成后，可立即编写压测脚本进行性能验证

### 界面概览

Web UI 提供了直观的压测管理界面，主要功能区域包括：

#### 1. 当前状态区域
- **服务状态**: 显示 Locust 服务的运行状态（停止/运行中）
- **状态指示器**: 绿色表示运行中，红色表示已停止
- **智能链接**: 根据访问方式自动显示相应的操作按钮

#### 2. 脚本管理区域
- **文件上传**: 支持拖拽或点击上传 `.py` 格式的测试脚本
- **脚本列表**: 显示已上传的所有脚本文件
- **脚本选择**: 下拉菜单选择要执行的脚本
- **文件操作**: 支持删除不需要的脚本文件

#### 3. 测试配置区域
- **目标主机**: 设置被测试的服务器地址
- **脚本选择**: 从已上传的脚本中选择要执行的文件
- **高级配置**: 可选的额外参数配置

#### 4. 控制操作区域
- **启动按钮**: 启动 Locust 压测服务
- **停止按钮**: 停止正在运行的压测服务
- **状态刷新**: 自动刷新服务状态

### 详细操作流程

#### 第一步：准备测试脚本

1. **编写测试脚本**
   ```python
   # 示例：简单的API测试脚本
   from locust import HttpUser, task, between
   
   class APIUser(HttpUser):
       wait_time = between(1, 3)
       
       @task
       def test_api(self):
           self.client.get("/api/health")
   ```

2. **保存为 .py 文件**
   - 文件名建议使用英文和下划线
   - 确保脚本语法正确，无语法错误

#### 📁 脚本上传最佳实践

1. **脚本命名规范**
   ```bash
   # 推荐命名格式
   trader_api_test.py          # 交易API测试
   user_login_stress.py        # 用户登录压测
   order_query_performance.py  # 订单查询性能测试
   ```

2. **脚本结构建议**
   ```python
   # 标准脚本模板
   from locust import HttpUser, task, between
   import json
   import random
   
   class MyTestUser(HttpUser):
       wait_time = between(1, 3)
       
       def on_start(self):
           """用户启动时执行，如登录等初始化操作"""
           self.login()
       
       def login(self):
           """登录逻辑"""
           pass
       
       @task(3)  # 权重为3，执行频率较高
       def high_frequency_task(self):
           """高频任务"""
           pass
       
       @task(1)  # 权重为1，执行频率较低
       def low_frequency_task(self):
           """低频任务"""
           pass
   ```

3. **快速迭代流程**
   ```bash
   # 开发流程示例
   编写脚本 → 上传到Web UI → 立即测试 → 查看结果 → 优化脚本 → 重新上传
   ```

#### 第二步：上传和管理脚本

1. **上传脚本文件**
   - 方式一：点击"选择文件"按钮，从文件浏览器选择
   - 方式二：直接拖拽 `.py` 文件到上传区域
   - 上传成功后会显示绿色提示信息
   - 系统会自动验证脚本语法和导入依赖

2. **管理脚本文件**
   - 查看已上传的脚本列表
   - 删除不需要的脚本（点击删除按钮）
   - 脚本会自动保存在服务器的 `scripts/` 目录
   - 支持脚本版本管理和备份

3. **脚本上传技巧**
   ```bash
   # 上传前检查清单
   ✓ 脚本语法正确
   ✓ 导入的模块都已安装
   ✓ 文件名符合命名规范
   ✓ 包含必要的错误处理
   ✓ 设置了合理的等待时间
   ```

4. **批量管理操作**
   - 支持一次上传多个脚本文件
   - 可以按类别组织脚本（如按功能模块分类）
   - 提供脚本搜索和过滤功能

#### 第三步：配置测试参数

1. **选择测试脚本**
   - 从下拉菜单中选择要执行的脚本
   - 确保选择的脚本是最新版本

2. **设置目标主机**
   ```
   开发环境: https://api.dev.stx365.com
   测试环境: https://api.test.stx365.com
   生产环境: https://api.prod.stx365.com
   ```

3. **验证配置**
   - 确保目标主机地址正确
   - 确认选择的脚本文件正确

#### 第四步：启动压力测试

1. **启动 Locust 服务**
   - 点击"启动 Locust"按钮
   - 等待状态变为"运行中"（通常需要 3-5 秒）
   - 观察状态指示器变为绿色
   - 系统会自动加载选定的测试脚本

2. **进入测试界面**
   - 点击"打开 Locust Web UI"按钮
   - 系统会在新标签页打开 Locust 原生界面
   - 如果是域名访问，需要先配置域名地址

3. **启动前检查**
   ```bash
   # 确认以下项目
   ✓ 目标服务器可访问
   ✓ 测试脚本已正确选择
   ✓ 网络连接稳定
   ✓ 系统资源充足
   ```

#### 第五步：配置并发参数

在 Locust Web UI 中：

1. **设置用户数量**
   - Number of users: 总并发用户数（建议从小开始，如 10）
   - Spawn rate: 每秒启动的用户数（建议 1-2）

2. **启动测试**
   - 点击"Start swarming"开始测试
   - 观察实时统计数据

3. **监控关键指标**
   - **RPS (Requests per second)**: 每秒请求数
   - **Response time**: 响应时间（平均值、中位数、95%分位数）
   - **Failure rate**: 失败率
   - **Active users**: 当前活跃用户数

#### 第六步：测试结果分析

1. **实时监控**
   - Statistics 标签：查看详细统计数据
   - Charts 标签：查看性能趋势图表
   - Failures 标签：查看失败请求详情

2. **性能评估**
   - 响应时间是否在可接受范围内
   - 错误率是否低于预期阈值
   - 系统是否能承受目标并发量

3. **测试调整**
   - 根据结果调整并发用户数
   - 修改测试脚本优化测试场景
   - 调整服务器配置优化性能

### 智能链接功能详解

#### IP 地址访问模式
当使用 IP 地址（如 `127.0.0.1:8088`）访问时：
- 直接显示"打开 Locust Web UI"按钮
- 点击后直接跳转到 `http://127.0.0.1:8089`
- 适用于本地开发和测试环境

#### 域名访问模式
当使用域名（如 `locust.example.com`）访问时：
- 显示域名配置表单
- 默认域名：`https://locust-service.test.stx365.com/`
- 可以修改为实际的生产环境域名
- 适用于生产环境和远程访问

### 常用操作技巧

#### 1. 快速测试流程
```bash
# 1. 准备简单测试脚本
echo 'from locust import HttpUser, task
class QuickTest(HttpUser):
    @task
    def test_health(self):
        self.client.get("/health")' > quick_test.py

# 2. 上传并启动
# 通过 Web UI 上传 quick_test.py
# 设置目标主机并启动测试
```

#### 2. 脚本热更新
- 修改脚本后重新上传（无需重启服务）
- 停止当前测试
- 选择新上传的脚本并重新启动
- 支持A/B测试对比不同脚本性能

#### 3. 多环境切换
- 保存不同环境的脚本文件
- 通过修改目标主机快速切换环境
- 使用环境变量管理配置
- 建议为每个环境创建专门的脚本

#### 4. 性能基线建立
- 记录首次测试的关键指标
- 建立性能基线数据
- 后续测试与基线对比分析
- 定期更新基线数据

#### 5. 脚本版本管理
```bash
# 推荐的脚本版本命名
api_test_v1.0.py     # 初始版本
api_test_v1.1.py     # 功能增强版本
api_test_hotfix.py   # 紧急修复版本
```

#### 6. 团队协作技巧
- 使用统一的脚本命名规范
- 在脚本中添加详细注释说明
- 定期清理不再使用的脚本
- 共享常用的脚本模板

### 最佳实践建议

#### 1. 测试前准备
- **环境检查**: 确保目标环境稳定可用
- **数据准备**: 准备充足的测试数据
- **监控就绪**: 确保服务器监控系统正常

#### 2. 测试执行策略
- **渐进式加压**: 从小并发开始，逐步增加
- **稳定性测试**: 在目标并发下运行足够时间
- **峰值测试**: 测试系统的极限承载能力

#### 3. 结果分析要点
- **响应时间分布**: 关注 95% 和 99% 分位数
- **错误模式分析**: 分析失败请求的原因
- **资源使用情况**: 监控 CPU、内存、网络使用率

#### 4. 安全注意事项
- **生产环境谨慎**: 避免对生产环境造成影响
- **数据安全**: 不要使用真实用户数据
- **访问控制**: 限制压测工具的访问权限
- **脚本安全**: 上传的脚本会在服务器执行，确保代码安全

#### 5. 脚本上传安全建议
```python
# 避免在脚本中硬编码敏感信息
# ❌ 错误示例
API_KEY = "sk-1234567890abcdef"  # 不要这样做

# ✅ 正确示例
import os
API_KEY = os.getenv("API_KEY", "default_test_key")

# 使用配置文件或环境变量
config = {
    "dev": {"host": "https://api.dev.example.com"},
    "test": {"host": "https://api.test.example.com"}
}
```

## 📝 脚本开发指南

### 基础脚本结构

```python
from locust import HttpUser, task, between
import random
import json

# 账号配置
accounts = [
    {"username": "910055", "password": "123456", "account_id": "M910055", "account_type": "M"},
    {"username": "910018", "password": "123456", "account_id": "M910018", "account_type": "M"},
]

class TraderUser(HttpUser):
    wait_time = between(1, 3)  # 请求间隔 1-3 秒
    
    def on_start(self):
        """用户启动时执行，通常用于登录"""
        self.account = random.choice(accounts)
        self.login()
    
    def login(self):
        """登录获取 token"""
        login_url = "/sso-server/test/test-login"
        params = {"c": self.account["username"], "p": self.account["password"]}
        
        with self.client.get(login_url, params=params, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("accessToken")
                self.headers = {"Authorization": self.token, "Content-Type": "application/json"}
            else:
                resp.failure(f"登录失败: {resp.text}")
    
    @task(1)
    def query_orders(self):
        """查询订单任务"""
        if not hasattr(self, 'headers'):
            return
            
        query_data = {
            "AccountID": self.account["account_id"],
            "AccountType": self.account["account_type"],
            "Exchange": "HK"
        }
        
        with self.client.post("/chief-trader-x/top/pc/order/listByAccountId", 
                             headers=self.headers,
                             data=json.dumps(query_data),
                             catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"查询失败: {resp.text}")
```

### 高级功能

#### 1. 签名认证

对于需要签名认证的接口，可以使用内置的签名功能：

```python
def _get_signature_headers(self, payload_dict: dict | None):
    """生成签名头"""
    # 详细实现见项目中的示例脚本
    pass
```

#### 2. 登录缓存

使用全局缓存避免重复登录：

```python
from gevent.lock import Semaphore

class TraderUser(HttpUser):
    account_token_cache: dict = {}
    account_login_lock: Semaphore = Semaphore()
```

#### 3. 任务权重

使用 `@task(weight)` 控制任务执行频率：

```python
@task(3)  # 权重为 3
def high_frequency_task(self):
    pass

@task(1)  # 权重为 1
def low_frequency_task(self):
    pass
```

### 内置脚本说明

项目提供了多个预置脚本，位于 `scripts/` 目录：

- `Trader/trader_locust.py`: 基础交易接口测试
- `Trader/trader_us_locust.py`: 美股交易接口测试
- `Trader/order_fees_locust.py`: 订单费用查询测试
- `Trader/order_modify_test.py`: 订单修改测试

## 🐳 部署方式

### 1. 本地开发部署

#### 基础安装
```bash
# 克隆项目
git clone https://dev.stx365.com/chief/chief-stresstest-locust.git
cd chief-stresstest-locust

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py

# 访问 http://localhost:8088
```

#### 开发环境配置
```bash
# 设置环境变量
export TARGET_HOST=https://api.dev.stx365.com
export LOCUST_FILE=Trader/trader_locust.py
export WEB_PORT=8088

# 启动开发服务
python app.py
```

### 2. Docker 单容器部署

#### 基础部署
```bash
# 构建镜像
docker build -t chief-stresstest-locust:latest .

# 运行容器（基础模式）
docker run --rm -p 8088:8088 chief-stresstest-locust:latest

# 运行容器（带环境变量）
docker run --rm \
  -p 8088:8088 \
  -e TARGET_HOST=https://api.dev.stx365.com \
  -e LOCUST_FILE=Trader/trader_locust.py \
  chief-stresstest-locust:latest
```

#### 高级配置
```bash
# 挂载自定义脚本目录
docker run --rm \
  -p 8088:8088 \
  -v $(pwd)/custom-scripts:/app/scripts \
  -e TARGET_HOST=https://api.test.stx365.com \
  chief-stresstest-locust:latest

# 使用自定义网络
docker network create locust-network
docker run --rm \
  --network locust-network \
  --name locust-service \
  -p 8088:8088 \
  chief-stresstest-locust:latest
```

#### 镜像构建选项
```bash
# 方式 A：使用默认镜像源
docker build -t chief-stresstest-locust:latest .

# 方式 B：使用国内镜像源（推荐）
docker build \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  -t chief-stresstest-locust:latest .

# 方式 C：多阶段构建（优化镜像大小）
docker build \
  --target production \
  -t chief-stresstest-locust:prod .
```

### 3. Docker Compose 部署

#### 基础 Compose 配置
```yaml
# docker-compose.yml
version: '3.8'

services:
  locust-web:
    build: .
    ports:
      - "8088:8088"
    environment:
      - TARGET_HOST=https://api.dev.stx365.com
      - LOCUST_FILE=Trader/trader_locust.py
      - WEB_PORT=8088
    volumes:
      - ./scripts:/app/scripts
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 多环境 Compose 配置
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  locust-dev:
    build: .
    ports:
      - "8088:8088"
    environment:
      - TARGET_HOST=https://api.dev.stx365.com
      - LOCUST_FILE=Trader/trader_locust.py
      - LOG_LEVEL=DEBUG
    volumes:
      - ./scripts:/app/scripts
      - ./dev-logs:/app/logs

  locust-test:
    build: .
    ports:
      - "8089:8088"
    environment:
      - TARGET_HOST=https://api.test.stx365.com
      - LOCUST_FILE=Trader/trader_us_locust.py
    volumes:
      - ./scripts:/app/scripts
      - ./test-logs:/app/logs
```

#### 启动命令
```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 启动生产环境
docker-compose up -d

# 查看日志
docker-compose logs -f locust-web

# 停止服务
docker-compose down
```

### 4. 生产环境部署

#### 生产环境镜像构建
```bash
# 构建生产镜像
docker build \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg BUILD_ENV=production \
  -t chief-stresstest-locust:prod-v1.0.0 .

# 标记最新版本
docker tag chief-stresstest-locust:prod-v1.0.0 chief-stresstest-locust:prod-latest
```

#### 生产环境运行
```bash
# 基础生产部署
docker run -d \
  --name locust-service \
  -p 8088:8088 \
  -e TARGET_HOST=https://api.prod.stx365.com \
  -e LOCUST_FILE=Trader/trader_locust.py \
  --restart unless-stopped \
  --memory=2g \
  --cpus=2 \
  chief-stresstest-locust:prod-latest

# 高可用部署
docker run -d \
  --name locust-service \
  -p 8088:8088 \
  -e TARGET_HOST=https://api.prod.stx365.com \
  -e LOCUST_FILE=Trader/trader_locust.py \
  -v /data/locust/scripts:/app/scripts \
  -v /data/locust/logs:/app/logs \
  --restart unless-stopped \
  --memory=4g \
  --cpus=4 \
  --log-driver=json-file \
  --log-opt max-size=100m \
  --log-opt max-file=3 \
  chief-stresstest-locust:prod-latest
```

#### 生产环境 Compose 配置
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  locust-service:
    image: chief-stresstest-locust:prod-latest
    ports:
      - "8088:8088"
    environment:
      - TARGET_HOST=https://api.prod.stx365.com
      - LOCUST_FILE=Trader/trader_locust.py
      - LOG_LEVEL=INFO
      - WEB_PORT=8088
    volumes:
      - /data/locust/scripts:/app/scripts
      - /data/locust/logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"

  # 可选：添加监控服务
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
```

### 5. Kubernetes 部署

#### 基础 K8s 配置
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-service
  labels:
    app: locust-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: locust-service
  template:
    metadata:
      labels:
        app: locust-service
    spec:
      containers:
      - name: locust
        image: chief-stresstest-locust:prod-latest
        ports:
        - containerPort: 8088
        env:
        - name: TARGET_HOST
          value: "https://api.prod.stx365.com"
        - name: LOCUST_FILE
          value: "Trader/trader_locust.py"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        volumeMounts:
        - name: scripts-volume
          mountPath: /app/scripts
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: scripts-volume
        persistentVolumeClaim:
          claimName: locust-scripts-pvc
      - name: logs-volume
        persistentVolumeClaim:
          claimName: locust-logs-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: locust-service
spec:
  selector:
    app: locust-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8088
  type: LoadBalancer
```

### 6. 容器化最佳实践

#### Dockerfile 优化
```dockerfile
# 多阶段构建示例
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.10-slim as production

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash locust

WORKDIR /app
COPY --from=builder /root/.local /home/locust/.local
COPY . .

# 设置权限
RUN chown -R locust:locust /app
USER locust

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8088/health || exit 1

EXPOSE 8088
CMD ["python", "app.py"]
```

#### 环境变量管理
```bash
# 创建环境变量文件
cat > .env << EOF
TARGET_HOST=https://api.prod.stx365.com
LOCUST_FILE=Trader/trader_locust.py
WEB_PORT=8088
LOG_LEVEL=INFO
MAX_WORKERS=4
EOF

# 使用环境变量文件
docker run --rm --env-file .env -p 8088:8088 chief-stresstest-locust:latest
```

#### 数据持久化
```bash
# 创建数据卷
docker volume create locust-scripts
docker volume create locust-logs

# 使用数据卷
docker run -d \
  --name locust-service \
  -p 8088:8088 \
  -v locust-scripts:/app/scripts \
  -v locust-logs:/app/logs \
  chief-stresstest-locust:latest
```

### 7. 部署验证

#### 健康检查
```bash
# 检查容器状态
docker ps
docker logs locust-service

# 检查服务健康
curl http://localhost:8088/health
curl http://localhost:8088/status

# 检查资源使用
docker stats locust-service
```

#### 性能测试
```bash
# 简单性能测试
ab -n 100 -c 10 http://localhost:8088/

# 压力测试
wrk -t12 -c400 -d30s http://localhost:8088/
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `TARGET_HOST` | 目标测试主机 | 无 | `https://api.dev.stx365.com` |
| `LOCUST_FILE` | 默认脚本文件 | `trader_locust_demo.py` | `Trader/trader_locust.py` |
| `WEB_PORT` | Web UI 端口 | `8088` | `8089` |
| `LOCUST_PORT` | Locust 服务端口 | `8089` | `8090` |

### 脚本配置

#### 账号配置

```python
accounts = [
    {
        "username": "910055",      # 登录用户名
        "password": "123456",      # 登录密码
        "account_id": "M910055",   # 账户ID
        "account_type": "M"        # 账户类型
    }
]
```

#### 签名配置

```python
# 签名相关头字段名称
SIGN_SECRET_ID_HEADER = "secretId"
SIGN_TIMESTAMP_HEADER = "timestamp"
SIGN_SIGNATURE_HEADER = "signature"
SECRET_FETCH_PATH = "/chief-trader-x/top/secret/once/fetch"
```

## 💡 最佳实践

### 1. 性能测试策略

- **渐进式加压**: 从小并发开始，逐步增加用户数
- **监控关键指标**: 重点关注 RPS、响应时间、错误率
- **设置合理的思考时间**: 使用 `wait_time = between(1, 3)` 模拟真实用户行为

### 2. 脚本开发建议

- **错误处理**: 使用 `catch_response=True` 进行自定义错误处理
- **数据隔离**: 不同账号使用不同的测试数据
- **资源清理**: 在 `on_stop` 方法中清理资源

### 3. 环境配置

- **开发环境**: 使用较小的并发数，便于调试
- **测试环境**: 模拟生产环境的负载特征
- **生产环境**: 谨慎进行压测，避免影响正常业务

### 4. 监控和分析

- **实时监控**: 关注系统资源使用情况
- **日志分析**: 收集和分析错误日志
- **性能基线**: 建立性能基线，便于对比分析

## 🔧 故障排除

### 常见问题与解决方案

#### 1. 服务启动问题

**问题：端口被占用**
```bash
# 症状
Error: [Errno 98] Address already in use

# 解决方案
# 查找占用端口的进程
netstat -tulpn | grep 8088
lsof -i :8088  # macOS/Linux

# Windows 查看端口占用
netstat -ano | findstr :8088

# 杀死进程
kill -9 <PID>           # Linux/Mac
taskkill /PID <PID> /F  # Windows

# 或者使用其他端口
python app.py --port 8089
```

**问题：Python 环境问题**
```bash
# 症状
ModuleNotFoundError: No module named 'locust'

# 解决方案
# 检查 Python 版本（需要 3.7+）
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 重新安装依赖
pip install -r requirements.txt
```

**问题：权限问题**
```bash
# 症状
Permission denied: '/app/logs'

# 解决方案
# 创建日志目录
mkdir -p logs
chmod 755 logs

# Docker 权限问题
docker run --user $(id -u):$(id -g) ...
```

#### 2. 依赖安装问题

**问题：pip 安装超时**
```bash
# 症状
ReadTimeoutError: HTTPSConnectionPool

# 解决方案
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或配置永久镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 增加超时时间
pip install --timeout 1000 -r requirements.txt
```

**问题：依赖版本冲突**
```bash
# 症状
ERROR: pip's dependency resolver does not currently take into account all the packages

# 解决方案
# 清理环境重新安装
pip uninstall -y -r requirements.txt
pip install -r requirements.txt

# 或使用 pip-tools
pip install pip-tools
pip-compile requirements.in
pip-sync requirements.txt
```

#### 3. Docker 相关问题

**问题：Docker 构建失败**
```bash
# 症状
ERROR [internal] load metadata for docker.io/library/python:3.10-slim

# 解决方案
# 清理 Docker 缓存
docker system prune -a

# 重新构建（无缓存）
docker build --no-cache -t chief-stresstest-locust:latest .

# 使用国内镜像源
docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple .
```

**问题：容器内存不足**
```bash
# 症状
Killed (OOM)

# 解决方案
# 增加内存限制
docker run --memory=4g --memory-swap=4g ...

# 检查内存使用
docker stats

# 优化 Python 内存使用
export PYTHONHASHSEED=0
export PYTHONUNBUFFERED=1
```

**问题：容器网络问题**
```bash
# 症状
curl: (7) Failed to connect to localhost port 8088

# 解决方案
# 检查端口映射
docker port <container_name>

# 检查防火墙
sudo ufw status
sudo iptables -L

# 使用主机网络模式
docker run --network host ...
```

#### 4. 压测脚本问题

**问题：脚本导入失败**
```bash
# 症状
ImportError: No module named 'scripts.Trader.trader_locust'

# 解决方案
# 检查文件路径
ls -la scripts/Trader/trader_locust.py

# 检查 Python 路径
export PYTHONPATH="${PYTHONPATH}:/app"

# 修复导入路径
# 在脚本中使用相对导入
from .common import *
```

**问题：认证失败**
```bash
# 症状
401 Unauthorized

# 解决方案
# 检查认证配置
# 确保 API 密钥正确
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

# 检查签名算法
# 确保时间戳和签名计算正确
```

**问题：请求超时**
```bash
# 症状
ReadTimeout: HTTPSConnectionPool

# 解决方案
# 增加超时时间
class WebsiteUser(HttpUser):
    connection_timeout = 60.0
    network_timeout = 60.0

# 或在请求中设置
response = self.client.get("/api/endpoint", timeout=30)
```

#### 5. 性能问题

**问题：压测性能不佳**
```bash
# 症状
RPS 很低，响应时间很长

# 解决方案
# 检查系统资源
top
htop
iostat

# 调整并发参数
# 减少用户数，增加 spawn rate
locust -u 100 -r 10

# 优化脚本
# 减少不必要的日志
# 使用连接池
# 避免重复计算
```

**问题：内存泄漏**
```bash
# 症状
内存使用持续增长

# 解决方案
# 监控内存使用
import psutil
import gc

# 在脚本中定期清理
def on_test_stop(self):
    gc.collect()

# 使用内存分析工具
pip install memory-profiler
python -m memory_profiler your_script.py
```

#### 6. Web UI 问题

**问题：Web UI 无法访问**
```bash
# 症状
This site can't be reached

# 解决方案
# 检查服务状态
curl http://localhost:8088/health

# 检查防火墙
sudo ufw allow 8088

# 检查绑定地址
# 确保绑定到 0.0.0.0 而不是 127.0.0.1
app.run(host='0.0.0.0', port=8088)
```

**问题：智能链接功能异常**
```bash
# 症状
域名配置表单不显示

# 解决方案
# 检查浏览器控制台错误
# 按 F12 查看 JavaScript 错误

# 检查网络请求
# 确保 /status 接口正常返回

# 清除浏览器缓存
Ctrl+F5 强制刷新
```

#### 7. 日志和监控问题

**问题：日志文件过大**
```bash
# 症状
磁盘空间不足

# 解决方案
# 配置日志轮转
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    'locust.log', maxBytes=100*1024*1024, backupCount=5
)

# 使用 Docker 日志限制
docker run --log-opt max-size=100m --log-opt max-file=3 ...
```

**问题：监控数据丢失**
```bash
# 症状
统计数据不准确

# 解决方案
# 检查时间同步
ntpdate -s time.nist.gov

# 确保数据持久化
# 使用外部存储（Redis、InfluxDB）

# 配置数据备份
# 定期导出统计数据
```

### 调试技巧

#### 1. 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 在 Locust 脚本中
import locust.log
locust.log.setup_logging("DEBUG")
```

#### 2. 使用调试模式
```bash
# 启动调试模式
python app.py --debug

# 单用户调试
locust -f your_script.py --headless -u 1 -r 1 -t 10s
```

#### 3. 网络抓包分析
```bash
# 使用 tcpdump
sudo tcpdump -i any -w capture.pcap port 8088

# 使用 Wireshark 分析
wireshark capture.pcap
```

#### 4. 性能分析
```python
# 使用 cProfile
python -m cProfile -o profile.stats your_script.py

# 分析结果
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

### 获取帮助

#### 1. 查看日志
```bash
# 应用日志
tail -f logs/locust.log

# Docker 日志
docker logs -f locust-service

# 系统日志
journalctl -u locust-service -f
```

#### 2. 健康检查
```bash
# 服务健康状态
curl http://localhost:8088/health

# 详细状态信息
curl http://localhost:8088/status

# 统计信息
curl http://localhost:8088/stats/requests
```

#### 3. 社区支持
- [Locust 官方文档](https://docs.locust.io/)
- [GitHub Issues](https://github.com/locustio/locust/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/locust)
- 内部技术支持：联系开发团队

#### 4. 报告问题
提交问题时请包含：
- 错误信息和堆栈跟踪
- 系统环境信息（OS、Python 版本、Docker 版本）
- 复现步骤
- 相关配置文件
- 日志文件（脱敏后）

```bash
# 收集环境信息
python --version
pip list
docker version
uname -a

# 导出配置
docker inspect locust-service > container-config.json
```

## 📚 API 参考

### Web UI API

#### 上传脚本
```http
POST /upload
Content-Type: multipart/form-data

file: <script.py>
```

#### 启动测试
```http
POST /start
Content-Type: application/json

{
    "script": "trader_locust.py",
    "host": "https://api.dev.stx365.com",
    "users": 10,
    "spawn_rate": 2
}
```

#### 停止测试
```http
POST /stop
```

#### 获取状态
```http
GET /status
```

### Locust 脚本 API

#### 基础用户类
```python
from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def my_task(self):
        self.client.get("/api/endpoint")
```

#### 事件钩子
```python
from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("测试开始")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("测试结束")
```

## 📞 技术支持

如果您在使用过程中遇到问题，可以通过以下方式获取帮助：

- **文档**: 查看本文档的详细说明
- **示例**: 参考 `scripts/` 目录中的示例脚本
- **日志**: 检查应用日志获取错误信息
- **社区**: 参与技术讨论和经验分享

## 📄 许可证

本项目采用内部许可证，仅供 Chief 团队内部使用。

---

**版本**: 1.0.0  
**更新时间**: 2024年1月  
**维护团队**: Chief 开发团队
